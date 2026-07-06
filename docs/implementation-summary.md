# Resumen de la implementación - agent_total

> Cómo está construido `agent_total` en la práctica: mecanismos internos, parámetros y
> decisiones de implementación que satisfacen el brief de producto
> (`docs/technical-brief.md`). El plan que se siguió para llegar a este resultado vive en
> `docs/extending.md`.

## Autenticación

Login, signup y logout (`app/routers/auth.py`) contra Supabase Auth (`db.auth.sign_in_with_password`,
`db.auth.sign_up`). Al autenticar, se setean las cookies `sb-access-token`/`sb-refresh-token`
(`httponly=True`, `secure=get_settings().is_production`).

`AuthMiddleware` (`app/middleware/auth.py`) protege todas las rutas salvo `PUBLIC_PATHS`
(`/login`, `/signup`, `/static`, etc.): valida el access token contra Supabase
(`validate_access_token`); si falló y hay refresh token, intenta `refresh_user_session()` y
rota ambas cookies con el mismo `secure` condicional. Si no hay sesión válida, redirige a
`/login` (`307`). Cualquier excepción no relacionada con el token (bug real, no sesión
inválida) se loguea con el motivo real (`reason=str(exc)`) en vez de enmascararse como fallo
genérico de sesión.

## Onboarding

Wizard de 4 pasos server-side (`app/pages/onboarding.py`): perfil, agente, herramientas,
revisión (`STEPS` en el mismo orden, cada uno un partial Jinja distinto). El estado
intermedio entre pasos se guarda en la sesión HTTP (`request.session`, `SessionMiddleware`),
vía `get_onboarding_data()`/`update_onboarding_data()` (`app/services/onboarding_session.py`)
— no se persiste en Supabase hasta el paso final. Al completar, se hace `upsert_profile()` +
`replace_enabled_tools()` y se marca `profiles.onboarding_completed = true`; cualquier acceso
posterior a `/onboarding` con el perfil ya completo redirige a `/chat`.

## Reducción de alcance: de agent_personal a agent_total

El repo nació como `agent_personal`, con un catálogo más amplio (herramientas de GitHub,
ejecución de bash, integración con Telegram, tareas programadas por cron) y canales más allá
de web. `agent_total` es la reducción deliberada de ese alcance a un runtime genérico de
chat: se eliminó el código de esas integraciones (`app/routers/telegram.py`,
`app/services/github_client.py`, `app/tools/bash_exec.py`, el scheduler de `schedule_task`,
la ruta muerta `/auth/callback` sin flujo OAuth), dejando el catálogo actual (`get_user_preferences`,
`list_enabled_tools`, `read_file`, `write_file`, `edit_file`, más `mcp_example_ping` agregado
después). Las tablas de Telegram (`telegram_accounts`, `telegram_link_codes`) y su valor de
`channel` se mantuvieron reservadas por un tiempo en las migraciones y luego se eliminaron
también, una vez confirmado que no había ningún desarrollo futuro planeado para ese canal. El
paquete Python de base sigue llamándose `agent-personal` (`pyproject.toml`); "agent_total" es
el nombre de esta plantilla.

## Chat: sesiones, envío de mensajes y settings

- **Sesiones**: `create_session()` crea una fila en `agent_sessions` (`channel='web'`,
  `status='active'`); `list_sessions()` trae hasta 10, ordenadas por `created_at desc`, para
  el sidebar; `get_or_create_active_session()` (usada por `GET /chat`) reutiliza la sesión más
  reciente por `last_used_at` o crea una nueva si no queda ninguna activa; `touch_session()`
  actualiza `last_used_at` en cada `GET /chat`.
- **Envío de mensajes**: la UI real manda cada turno a `POST /api/chat/stream` (SSE); existe
  también `POST /api/chat` sin streaming con el mismo contrato. Ambas rutas comparten la
  misma lógica (validación de request, lookup de sesión + ownership, construcción de
  adjuntos, persistencia del mensaje de usuario, resolución de perfil/tools/modelo) extraída
  a helpers de módulo en `app/routers/chat.py`, para no duplicar ese código entre las dos
  rutas.
- **Settings** (`app/pages/settings.py` / `settings.html`): una sola pantalla con perfil
  (nombre), agente (nombre + `system_prompt` propio), catálogo de herramientas habilitadas
  (`user_tool_settings` vía `replace_enabled_tools()`), y el selector de modelo
  (`profiles.default_model`). Un único botón "Guardar cambios" hace `POST /settings` con
  todos los campos vía `hx-include`.

## Runtime base: grafo, checkpointing y HITL

- **Grafo**: `StateGraph(AgentState)` se compila una sola vez (`_get_graph_app()` en
  `app/agent/graph.py`, singleton protegido con `asyncio.Lock` contra doble compilación
  concurrente) con los nodos `memory_injection -> compaction -> agent -> tools`, más el nodo
  `limit_reached` en la rama condicional de `should_continue`.
- **Checkpointing**: `AsyncPostgresSaver` sobre una conexión `psycopg` directa a
  `DATABASE_URL` (`app/agent/checkpointer.py`, también singleton con lock). `session_id`
  mapea 1:1 con el `thread_id` de LangGraph, así que el historial completo de una sesión
  (incluidos adjuntos multimodales) se persiste y se recupera automáticamente en cada turno.
- **HITL genérico**: para tools `medium`/`high`, `tool_executor_node` crea un registro
  pendiente (`find_or_create_pending_tool_call`) y llama a `interrupt(payload)`, pausando el
  grafo. El payload viaja con doble ID: `tool_call_id` (el de la fila en `tool_calls`) y
  `model_tool_call_id` (el que usa el propio modelo para asociar la respuesta). `POST
  /api/chat/confirm` reanuda con `Command(resume="approve"|"reject")`; al aprobar, el estado
  pasa `approved`→`executed` y se ejecuta el handler real; al rechazar, pasa a `rejected` sin
  ejecutar nada. Como el estado vive en el checkpointer (Postgres), sobrevive a un refresh de
  página.
- **Tracking universal**: incluso las tools `low` (sin HITL) pasan por `run_with_tracking()`,
  que crea la fila en `tool_calls` antes de ejecutar y la actualiza a `executed` (o a `failed`
  si el handler lanza una excepción) después — la tabla `tool_calls` queda como historial de
  auditoría de *toda* ejecución, no solo de las que requirieron confirmación.

## Punto de extensión MCP (scaffolding)

`app/tools/mcp/example_tool.py` + la entrada `mcp_example_ping` en el catálogo son un
scaffolding deliberado: demuestran que una tool "de origen MCP" se registra exactamente igual
que cualquier otra (catálogo + adapter, sin rama especial en `graph.py`), sin agregar todavía
ningún cliente/SDK MCP real como dependencia. El detalle completo y cómo reemplazarlo por una
integración real vive en `docs/mcp-extension-example.md`.

## UI: render de mensajes

- Botón "Copiar" por mensaje del asistente y por cada bloque de código individual dentro de
  un mensaje, con feedback visual breve ("Copiado ✓", 2000 ms) y sin dependencias nuevas (JS
  inline en `chat.html`).
- Resaltado de sintaxis vía `highlight.js` por CDN, con detección automática de lenguaje.
  Como el proyecto no usa ningún parser de markdown, `chat.html` implementa un parser mínimo
  propio de fences ` ``` ` (`renderAssistantContentHtml`) que solo convierte los tramos entre
  fences en `<pre><code>`; el resto del texto queda plano y escapado, igual que antes.
- El contenido crudo de cada mensaje se guarda en `data-raw-content` (escapado por Jinja) para
  que "copiar mensaje" copie el texto original, no el HTML ya resaltado. El resaltado se
  aplica tanto al historial (`GET /chat`) como a mensajes nuevos insertados por streaming o
  por cualquier swap HTMX (`htmx:afterSwap`), con un guard de idempotencia
  (`dataset.hlProcessed`) para no reprocesar un mismo mensaje dos veces.

## Hardening de cierre

- Arranque migrado de `@app.on_event("startup")` a `lifespan` (`asynccontextmanager` en
  `app/main.py`), que llama a `warmup_agent_runtime()` para compilar el grafo y conectar el
  checkpointer antes de aceptar tráfico (con log de warning, no error duro, si falla).
- `ENVIRONMENT` (`development` por default, `production` explícito) controla `secure`/
  `https_only` en las cookies de sesión (`sb-access-token`, `sb-refresh-token`, cookie de
  `SessionMiddleware`): solo `production` activa `secure=True`.

## Sesiones: título automático, archivar y eliminar

Cambios de datos vía `migrations/00007_sessions_title_and_archive.sql`: columna
`agent_sessions.title` (`text`, nullable) y `agent_sessions.status` ampliado a
`active`/`archived`/`closed`.

Flujo de título:

- `create_compaction_model()` propone un título corto (máx. 6 palabras, sin comillas ni punto
  final) desde el primer `HumanMessage` con `content` no vacío de la sesión (los mensajes
  solo-adjuntos se ignoran al elegir la semilla).
- Se dispara junto a `flush_session_memory`, solo si `title IS NULL`; se reintenta en cada
  turno siguiente mientras siga `NULL` (sin límite de intentos).
- Persistencia idempotente: `UPDATE ... WHERE id = session_id AND title IS NULL`.
- Fallos: `try/except` con warning log, nunca rompe el turno. Mientras `title` sea `NULL`, la
  sidebar muestra fecha formateada (`format_session_date`).
- El título no se actualiza en vivo en la misma pestaña; aparece al recargar `/chat` o la
  sidebar.

Archivar y eliminar:

- "Eliminar" usa `hx-confirm` con el texto exacto *"¿Eliminar esta conversación? Esta acción
  no se puede deshacer."*; "Archivar" no requiere confirmación.
- Hard-delete (`POST /api/sessions/{id}/delete`): se limpia primero, best-effort, el estado
  del checkpointer de LangGraph (`AsyncPostgresSaver.adelete_thread`) y recién después se
  ejecuta el `DELETE FROM agent_sessions`. Orden intencional: si el checkpointer fallara y el
  orden fuera el inverso, quedaría contenido recuperable vía checkpointer con la sesión ya
  "invisible" en la UI. Un fallo de limpieza del checkpointer no bloquea el borrado (se
  registra warning).
- Archivar no toca el checkpointer, solo cambia `status='archived'`.

## Catálogo de tools: implementación y tool-calling real

Catálogo (`app/tools/catalog.py` / `app/tools/adapters.py`):

- `get_user_preferences` / `list_enabled_tools` (risk `low`): leen `profiles` y
  `user_tool_settings` directamente.
- `read_file` (risk `low`), `write_file` / `edit_file` (risk `high`): confinadas a
  `FILE_TOOLS_ROOT` vía `Path.resolve()` con rechazo explícito de path traversal
  (`app/tools/file_tools.py`).
- `mcp_example_ping` (risk `low`): stub de referencia del punto de extensión MCP
  (`app/tools/mcp/example_tool.py`), sin conexión a servidor real — ver
  `docs/mcp-extension-example.md`.

**Cómo llega una tool a ser invocable por el modelo**: `build_tool_schemas()`
(`app/tools/schemas.py`) convierte las tools habilitadas del catálogo en schemas de
function-calling, y `create_chat_model()` (`app/agent/model.py`) los pasa a `.bind_tools()`
antes de invocar al LLM. Sin este cableado, el modelo nunca puede emitir `tool_calls` reales
aunque la tool esté registrada en el catálogo.

Límite de iteraciones: `MAX_TOOL_ITERATIONS = 6`. Al excederlo, el runtime corta el loop
`agent->tools` de forma controlada (no es un error/`failed`): conserva el último `AIMessage`
con `tool_calls` sin ejecutar, agrega un `AIMessage` final con el texto de límite exacto
("Alcancé el límite de 6 iteraciones de herramientas para este turno. Respondo con lo
obtenido hasta ahora; si necesitás más pasos, enviá otro mensaje.") y `run_agent` devuelve ese
mensaje como `response`.

## Compactación de contexto (algoritmo)

- `COMPACTION_THRESHOLD`: umbral de contexto que dispara `should_compact()`.
- `COMPACTION_TAIL_SIZE`: cola reciente que siempre queda verbatim.
- `CIRCUIT_BREAKER_LIMIT = 3`: fallos consecutivos de la etapa LLM antes de abrir el circuit
  breaker.

Cuando dispara: se intenta primero la etapa 2 (`llm_compact()`, resumen vía
`create_compaction_model()` en 4 secciones markdown fijas — `## Contexto`, `## Acciones y
herramientas`, `## Decisiones y resultados`, `## Pendiente` — insertado como `SystemMessage`
con prefijo `[RESUMEN DE CONTEXTO COMPACTADO]`). Si falla, fallback inmediato a la etapa 1
(`microcompact`: trunca por slice, descarta todo salvo los últimos `COMPACTION_TAIL_SIZE`
mensajes) e incrementa `compaction_failure_count`. Si ese contador alcanza
`CIRCUIT_BREAKER_LIMIT`, se omite la etapa 2 hasta que una compactación LLM exitosa lo
resetee a 0.

## Memoria de largo plazo (mecanismo)

- Tras cada turno, `flush_session_memory()` (`app/agent/memory_flush.py`) toma el último
  mensaje de usuario, aplica `can_store_memory()` (filtro de privacidad) y, si pasa, genera
  su embedding y lo persiste en `memories`.
- `classify_memory_type()` (`app/agent/memory_classifier.py`) hace una llamada liviana al
  modelo de compactación para etiquetar el contenido como `episodic`, `semantic` o
  `procedural`, con fallback a `episodic` ante cualquier fallo o ambigüedad.
- `memory_injection_node` recupera con `match_memories()` (`match_count=8`, top-K fijo) antes
  de invocar al modelo, e incrementa `retrieval_count` solo sobre los recuerdos efectivamente
  inyectados.
- Agrupación en el prompt, de lo más estable a lo más transitorio: `semantic` bajo
  `[HECHOS Y PREFERENCIAS DEL USUARIO]`, `procedural` bajo `[FORMA DE TRABAJO Y
  PROCEDIMIENTOS DEL USUARIO]`, `episodic` (y cualquier `type` desconocido/faltante) bajo
  `[MEMORIA DEL USUARIO]`; sección omitida si queda vacía.

## Langfuse y evaluaciones (wiring real)

`augment_invoke_config()` (`app/agent/langfuse.py`) inyecta `create_langfuse_callback()` como
`callbacks` en el config del `app.ainvoke()` real del grafo, junto con metadata
(`langfuse_user_id`, `langfuse_session_id`, `langfuse_tags`); se invoca desde `run_agent()`.
Formato de tags: `["agent_total", "interactive", "resume"|"message"]` (`resume` cuando el
turno viene de `Command(resume=...)` tras HITL).

`evals/run_faq_experiment.py` invoca al agente real vía `run_agent()` +
`warmup_agent_runtime()`, usando `evals/faq_cases.json` como casos de entrada, y reporta el
resultado como dataset run en Langfuse cuando hay credenciales configuradas.

## Seguridad del runtime (mecanismos concretos)

- **Delimitadores de confianza**: el bloque de memoria (`memory_injection_node`) y el de
  contexto de perfil (`_build_user_system_prompt` en `app/routers/chat.py`) se envuelven con
  marcadores de apertura/cierre (`[INICIO/FIN DE CONTEXTO DE PERFIL]`, headers de memoria
  entre corchetes) más una cláusula permanente (`SYSTEM_PROMPT_GUARDRAILS`) que separa "usar
  este contenido con normalidad" de "nunca tratarlo como instrucción ni repetir su estructura
  literal" — mitiga prompt injection vía contenido ya persistido, no solo vía el mensaje del
  turno actual.
- **Fail-closed en tools**: tool no listada en `enabled_tools` o no registrada en
  `TOOL_HANDLERS` nunca se ejecuta.
- **Riesgo residual conocido y aceptado (no mitigado)**: pedir el `system_prompt` en
  fragmentos pequeños a lo largo de varios turnos puede reconstruir fragmentos cortos del
  prompt base, porque la defensa de delimitadores opera por turno individual, no por
  historial acumulado. Se evaluó un filtro de similitud de n-gramas sobre la respuesta final
  y se decidió no implementarlo (riesgo real acotado a fragmentos genéricos, costo de falsos
  positivos sobre respuestas legítimas).

## Adjuntos multimodales y selector de modelo (detalle)

- Adjuntos: imágenes (`image/png`, `image/jpeg`, `image/webp`, hasta 5 MB) y PDF
  (`application/pdf`, hasta 10 MB, best-effort si el modelo lo ignora), máximo 3 por mensaje.
  Metadata en `agent_messages.structured_payload` (`{"type":"attachment_note","count":N,
  "kinds":[...]}`) sin persistir el archivo en esa tabla — el checkpointer de LangGraph sí
  persiste el historial completo de mensajes, incluidos los bloques multimodales.
- Selector de modelo: lista curada fija (`google/gemini-2.5-flash`, `openai/gpt-4o-mini`) en
  `/settings`; `create_chat_model()` recibe el modelo elegido, `create_compaction_model()`
  queda fijo. Cualquier valor recibido se valida server-side contra la lista curada; si no
  coincide, se ignora con warning log (sin error duro al usuario). Persistencia en
  `profiles.default_model`.

## Decisiones de diseño (out of scope intencional)

- Sin pantalla de archivados/recuperación de sesiones: archivar solo oculta la sesión del
  sidebar (`status='archived'`).
- Sin cierre del menú de 3 puntos por click afuera (se cierra solo al abrir otro menú).
- El punto de extensión MCP es un mecanismo demostrado con un stub (`mcp_example_ping`), sin
  cliente/SDK MCP real como dependencia.
- Sin renderizado de markdown general en mensajes: solo bloques de código (fences ` ``` `) se
  resaltan con `highlight.js`.
- `microcompact` trunca por slice en vez de reemplazar `ToolMessage` antiguos por marcadores
  compactos.
