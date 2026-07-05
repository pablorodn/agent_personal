# Technical Brief - agent_total

> Documento rector de arquitectura y alcance para `agent_total`: plantilla de agente genérico y extensible.
> Stack base: FastAPI + LangGraph + Supabase + OpenRouter + Langfuse.

## 1) Resumen ejecutivo

`agent_total` deja de centrarse en tools de dominio específicas y pasa a enfocarse en:

- Runtime robusto y reusable.
- Políticas de riesgo y HITL genéricas.
- Persistencia y trazabilidad confiables.
- Punto de extensión claro para nuevas tools (incluyendo futuras integraciones MCP).

El objetivo no es reescribir el runtime por cada integración, sino extenderlo por catálogo + handlers.
El detalle de decisiones de implementación y de cómo se resolvió cada discrepancia detectada durante la construcción se registra en `docs/agent_total-changelog.md`.

## 2) Alcance actual y estado real

### Implementado en código hoy

- Autenticación web: login, signup, logout.
- Onboarding wizard de 4 pasos (perfil, agente, herramientas, revisión).
- Chat web multi-sesión con sidebar, título automático de sesión, archivado y hard-delete con limpieza de checkpointer.
- Runtime LangGraph con grafo `memory_injection -> compaction -> agent -> tools`.
- Checkpointing con `AsyncPostgresSaver`.
- HITL genérico con `interrupt()` y `Command(resume=...)`, usando doble ID (`tool_calls.id` y `model_tool_call_id`).
- File tools con `FILE_TOOLS_ENABLED` y confinamiento de paths.
- Estructura de catálogo/política de riesgo como mecanismo central, con punto de extensión MCP demostrado (registro vía catálogo + adapter, sin tocar `graph.py`).
- Memoria de largo plazo end-to-end: inyección real en el prompt (`memory_injection_node`) con `match_memories()` invocado en el flujo real y filtro de privacidad antes de persistir.
- Compactación de contexto en dos etapas (resumen LLM + truncado duro de respaldo) con circuit breaker.
- Langfuse conectado al `invoke` real del grafo.
- Evaluaciones (`evals/run_faq_experiment.py`) corriendo contra el runtime real (`run_agent()`), no un stub.
- Adjuntos multimodales (imagen + PDF) y selector de modelo con persistencia en `profiles.default_model`.
- Hardening de cierre: arranque vía `lifespan`, cookies `secure`/`https_only` condicionales por `ENVIRONMENT`.

### Fuera de alcance a propósito (no es "pendiente", es decisión consciente)

Ver `docs/agent_total-as-built.md` para el detalle completo. En síntesis:

- Pantalla de archivados/recuperación de sesiones.
- Click-outside-to-close en el menú de 3 puntos de sesión.
- Integración MCP real (el punto de extensión es un scaffolding stub, sin cliente/SDK MCP real).
- Renderizado de markdown general en mensajes (solo bloques de código con `highlight.js`).
- Comportamiento ideal de `microcompact` con marcadores en vez de truncado duro (ver §7).

## 3) Arquitectura base

Separación por capas:

- `app/routers` y `app/pages`: entrada HTTP y contratos HTMX/SSR.
- `app/agent`: runtime LangGraph.
- `app/tools`: catálogo, schemas y adapters.
- `app/db`: acceso a Supabase y queries.
- `app/services`: servicios transversales.

Invariante central:

```text
START -> memory_injection -> compaction -> agent -> tools -> compaction -> ... -> END
```

## 4) Rutas en alcance (web + API)

Tabla canónica en alcance para `agent_total`:

| Método + ruta | Tipo | Respuesta |
| --- | --- | --- |
| `POST /login` | Página | `HX-Redirect` o partial con error |
| `POST /signup` | Página | `HX-Redirect` o partial con error |
| `POST /logout` | Página | `HX-Redirect: /login` |
| `GET /onboarding` | Página | HTML |
| `GET /onboarding/step/{n}` | Página | Partial HTML |
| `POST /onboarding/step/{n}` | Página | Partial HTML |
| `POST /onboarding/finish` | Página | `HX-Redirect: /chat` |
| `GET /chat` | Página | HTML |
| `GET /chat/session/{id}` | Página | Lista de mensajes renderizados |
| `GET /settings` | Página | HTML |
| `POST /settings` | Página | Partial de estado guardado |
| `POST /api/chat` | API | Partial de respuesta o panel HITL |
| `POST /api/chat/stream` | API | `text/event-stream` (SSE): eventos `tick`, `message_html`, `error` |
| `POST /api/chat/confirm` | API | Partial de respuesta final |
| `GET /api/sessions` | API | JSON de sesiones |
| `POST /api/sessions` | API | Partial de item de sesión |
| `POST /api/sessions/{id}/clear` | API | String vacío |
| `POST /api/sessions/{id}/archive` | API | `HX-Redirect: /chat` (si archiva la sesión actual) o partial vacío para remover item |
| `POST /api/sessions/{id}/delete` | API | `HX-Redirect: /chat` (si elimina la sesión actual) o partial vacío para remover item |

`POST /api/chat/stream` es la ruta que usa realmente la UI de `chat.html` (vía `fetch` + lectura de stream SSE, no HTMX) para enviar cada turno de chat, incluyendo texto y adjuntos multimodales. `POST /api/chat` es una ruta equivalente sin streaming (responde con el partial de mensaje ya completo), mantenida y con la misma cobertura funcional (incluye adjuntos y selector de modelo desde Fase 9/10) para no dejar el contrato documentado sin implementación, pero no es la que invoca el formulario de chat real.

### Capacidades objetivo nuevas en rutas

- Adjuntos multimodales en chat desde `/chat`, enviados por la UI vía `POST /api/chat/stream` (también soportado por `POST /api/chat`).
- Selector de modelo en chat, resuelto y persistido en ambas rutas de envío (`POST /api/chat` y `POST /api/chat/stream`) en `profiles.default_model`.

### Sesiones: título automático, archivar y eliminar

Cambios de datos aplicados vía `migrations/00007_sessions_title_and_archive.sql` (Fase 13, migración independiente, ya aplicada contra Supabase real):

- Agregar `agent_sessions.title` (`text`, nullable, default `null`).
- Ampliar `agent_sessions.status` para aceptar `archived` además de `active` y `closed`.
- El ajuste del CHECK se hace con patrón `DROP CONSTRAINT IF EXISTS ...` + `ADD CONSTRAINT ...`.

Flujo de generación de título:

- Se usa `create_compaction_model()` para proponer un título corto (máx. 6 palabras, sin comillas ni punto final) desde el primer mensaje de usuario.
- Definición operativa de "primer mensaje de usuario": el primer `HumanMessage` de la sesión con `content` no vacío. Los mensajes solo-adjuntos (sin texto, ver §10.1) se ignoran al elegir la semilla; si ningún mensaje de usuario tiene texto todavía, no se genera título en ese turno (`title` sigue `NULL`).
- Trigger de ejecución: tras turnos completados sin confirmación pendiente, en el mismo punto de fire-and-forget donde corre `flush_session_memory`, solo si `agent_sessions.title IS NULL`.
- Reintentos: sin límite — se reintenta en cada turno siguiente mientras `title IS NULL` (no hay contador de intentos; la migración 00007 solo agrega la columna `title`).
- Idempotencia: persistir con `UPDATE ... WHERE id = session_id AND title IS NULL`.
- Fallos: patrón `try/except` con warning log; nunca rompe el turno de chat.
- Fallback UI: mientras `title` sea `NULL`, la sidebar sigue mostrando fecha formateada (`format_session_date`).

Archivar y eliminar:

- Confirmación en UI: el botón "Eliminar" usa `hx-confirm` con el texto exacto *"¿Eliminar esta conversación? Esta acción no se puede deshacer."*; el botón "Archivar" no requiere confirmación.
- Orden de operaciones del hard-delete (`POST /api/sessions/{id}/delete`): se limpia primero, best-effort, el estado del checkpointer de LangGraph para ese `thread_id` (`AsyncPostgresSaver.adelete_thread`); recién después se ejecuta el `DELETE FROM agent_sessions` real. Este orden es intencional: maximiza que el contenido de chat quede efectivamente inaccesible tras el borrado — si el checkpointer fallara y el orden fuera el inverso, quedaría contenido recuperable vía checkpointer con la sesión ya "invisible" en la UI, que es exactamente el riesgo que este mecanismo busca evitar. Si la limpieza del checkpointer falla, no bloquea el borrado de `agent_sessions` (se registra warning).
- El archivado (`/archive`) NO afecta el estado del checkpointer, solo cambia `status='archived'`.

Aclaración de experiencia de usuario:

El título de sesión no se actualiza en vivo dentro de la misma pestaña abierta; aparece la próxima vez que se carga `/chat` o se recarga la sidebar. No se implementa polling ni websockets en esta fase.

## 5) Catálogo de tools y política de riesgo

El mecanismo (catálogo + `risk` + `TOOL_HANDLERS`) se conserva como contrato central.

Catálogo concreto de `agent_total` (alcance objetivo):

- `get_user_preferences`
- `list_enabled_tools`
- `read_file`
- `write_file`
- `edit_file`

Reglas:

- `low`: ejecución directa.
- `medium/high`: pausa HITL obligatoria en modo interactivo.
- Herramientas desconocidas o mal registradas se tratan fail-closed.

### Límites de ejecución del runtime

`MAX_TOOL_ITERATIONS = 6`. Si una ejecución de turno excede este límite de ciclos `agent->tools`, el runtime corta el loop sin ejecutar más tools (no se marca como error/`failed`; es un corte controlado, no una falla).

**Texto exacto al usuario** (constante `MAX_TOOL_ITERATIONS_LIMIT_MESSAGE`):

> Alcancé el límite de 6 iteraciones de herramientas para este turno. Respondo con lo obtenido hasta ahora; si necesitás más pasos, enviá otro mensaje.

**Comportamiento de estado al cortar** (nodo `limit_reached`):

- Se conserva el último `AIMessage` con `tool_calls` **sin ejecutar** en el historial (no se agregan `ToolMessage` para esas llamadas).
- Se agrega un `AIMessage` final con el texto de límite (sin `tool_calls`).
- `run_agent` devuelve ese último `AIMessage` como `response`.

## 6) File tools

`read_file`, `write_file`, `edit_file`:

- Gate por `FILE_TOOLS_ENABLED` (solo `"true"` habilita).
- Confinamiento estricto a raíz permitida.
- Rechazo explícito de path traversal y rutas fuera del root.

## 7) Compactación de contexto (especificación completa)

Parámetros y diseño:

- `COMPACTION_THRESHOLD`: umbral de contexto.
- `MICROCOMPACT_KEEP_RECENT`: preserva mensajes recientes de tool (comportamiento ideal pendiente).
- `COMPACTION_TAIL_SIZE`: cola reciente verbatim.
- `CIRCUIT_BREAKER_LIMIT`: **3** — fallos consecutivos de la etapa LLM antes de abrir el circuit breaker.

### Interacción etapa 1 / etapa 2

Cuando `should_compact()` dispara (contexto >= umbral):

1. **Etapa 2 (LLM)** se intenta primero: `llm_compact()` resume el historial antiguo y preserva la cola verbatim.
2. Si la etapa 2 **falla**, fallback inmediato a **etapa 1 (microcompact)**; se incrementa `compaction_failure_count`.
3. Si `compaction_failure_count >= CIRCUIT_BREAKER_LIMIT` (circuit breaker abierto), se omite la etapa 2 y solo se aplica etapa 1 hasta que una compactación LLM exitosa resetee el contador a 0.

La etapa 1 **no queda obsoleta**: sigue siendo el fallback garantizado ante fallos LLM y cuando el circuit breaker está abierto.

### Etapa 1 - Microcompact

- Sin LLM.
- Truncado duro por slice: descarta todos los mensajes salvo los últimos `COMPACTION_TAIL_SIZE`.
- Pierde información de contexto en vez de compactarla (aceptable como fallback).

### Etapa 2 - Compactación con LLM

- Usa `create_compaction_model()`.
- Resumen estructurado por secciones markdown fijas (nombres exactos):
  - `## Contexto`
  - `## Acciones y herramientas`
  - `## Decisiones y resultados`
  - `## Pendiente`
- El resumen se inserta como un único `SystemMessage` con prefijo `[RESUMEN DE CONTEXTO COMPACTADO]`.
- Preserva cola reciente verbatim: los últimos `COMPACTION_TAIL_SIZE` mensajes no se modifican.
- Circuit breaker: tras `CIRCUIT_BREAKER_LIMIT` fallos consecutivos de la etapa LLM, se omite LLM y solo aplica etapa 1.

Comportamiento ideal pendiente de microcompact:

- Reemplazar contenido de `ToolMessage` antiguos por marcadores compactos en lugar de descartarlos.

## 8) Memoria de largo plazo (especificación y gaps)

Especificación objetivo:

- Extracción post-turno.
- Embeddings.
- Almacenamiento vectorial.
- Búsqueda por similitud.
- Inyección de recuerdos relevantes al prompt en `memory_injection_node`.
- Recuperación con `match_count=8` (top-K fijo).
- Incremento de contador de recuperación con `increment_memory_retrieval_count` sobre recuerdos efectivamente inyectados.
- Política de privacidad aplicada antes de persistir.

Estado real actual:

- `memory_injection_node` inyecta memorias reales en el prompt: `match_memories()` está
  conectado al flujo real desde la Fase 4, confirmado empíricamente (el asistente reconoce
  al usuario usando contexto de sesiones anteriores).

Alcance real de tipos de memoria:

- La columna `type` de la tabla `memories` (`migrations/00004_long_term_memory.sql`) permite
  3 valores: `episodic`, `semantic`, `procedural`. Los 3 tienen productor real en el código:
  `flush_session_memory()` clasifica cada turno del usuario vía `classify_memory_type()`
  (`app/agent/memory_classifier.py`), una llamada liviana al mismo modelo de compactación
  (`create_compaction_model()`) usada para generar el título de sesión
  (`app/agent/session_title.py`), con el mismo patrón de manejo de errores (fallback a
  `episodic` ante cualquier fallo o respuesta ambigua — nunca a `procedural`).
  `memory_injection_node` agrupa las memorias inyectadas en el prompt en 3 secciones, en este
  orden (de lo más estable a lo más transitorio): `semantic` bajo el header
  `[HECHOS Y PREFERENCIAS DEL USUARIO]`, `procedural` bajo
  `[FORMA DE TRABAJO Y PROCEDIMIENTOS DEL USUARIO]`, y `episodic` (incluyendo cualquier valor
  de `type` desconocido o faltante) bajo `[MEMORIA DEL USUARIO]`; cada sección se omite si
  queda vacía.

## 9) Langfuse y evaluaciones

Objetivo:

- Conectar callback y metadata al `app.ainvoke()` del runtime:
  - `langfuse_user_id`
  - `langfuse_session_id`
  - `langfuse_tags`
  - `langfuse_tags = ["agent_total", "interactive", "resume"|"message"]` (sin variante `cron` mientras el canal activo sea web)
- Evaluaciones automáticas contra runtime real.

Estado real actual:

- `augment_invoke_config()` (`app/agent/langfuse.py`) inyecta `create_langfuse_callback()` como
  `callbacks` en el config del `app.ainvoke()` real del grafo, junto con la metadata
  (`langfuse_user_id`, `langfuse_session_id`, `langfuse_tags`); se invoca desde `run_agent()`
  en `app/agent/graph.py`.
- `evals/run_faq_experiment.py` invoca al agente real (`run_agent()` vía `warmup_agent_runtime()`
  + sesiones reales), no es un stub.

## 10) Nuevas capacidades objetivo

### 10.1 Adjuntos multimodales en chat

- Entrada de archivo en `/chat`.
- Tipos permitidos: imágenes (`image/png`, `image/jpeg`, `image/webp`) y PDF (`application/pdf`).
- Envío al LLM como bloques multimodales (`image` / `document` de LangChain).
- Soporte de imágenes garantizado para ambos modelos de la lista curada.
- Soporte de PDF en modo best-effort: se envía como bloque `document`, pero no todos los modelos lo procesan igual; si el modelo ignora el PDF, el turno continúa sin bloquear al usuario y no se trata como error.
- Cuando hay adjuntos, guardar metadata en `agent_messages.structured_payload` del mensaje de usuario (ej. `{"type":"attachment_note","count":N,"kinds":[...]}`) sin persistir contenido de archivo.
- La UI renderiza indicador genérico de adjuntos (ej. `📎 Se enviaron N archivo(s)`) incluso tras recargar sesión.
- Sin persistencia de adjuntos en esta etapa.
- El mensaje de texto es opcional cuando el turno incluye adjuntos: se permite enviar solo adjuntos sin texto acompañante.

Límites iniciales propuestos:

- Imagen: hasta 5 MB por archivo.
- PDF: hasta 10 MB por archivo.
- Máximo 3 adjuntos por mensaje.

### 10.2 Selector de modelo en UI

- Set curado inicial (única fuente de verdad del selector hasta futura sesión de documentación dedicada):
  - `google/gemini-2.5-flash`
  - `openai/gpt-4o-mini`
- `create_chat_model()` recibe el modelo elegido para cada turno.
- `create_compaction_model()` se mantiene fijo y no seleccionable por usuario.
- El valor de modelo recibido desde formulario debe validarse server-side contra la lista curada antes de invocar `create_chat_model()`.
- Si el valor no está permitido, se ignora y se usa modelo por defecto; se registra warning en logs sin error duro para el usuario.
- Persistencia de preferencia en nueva columna `profiles.default_model`.

### 10.3 Mejoras de UI SSR + HTMX

- Botón "Copiar" por cada mensaje del asistente.
- Resaltado de sintaxis en bloques de código usando CDN (por ejemplo, `highlight.js`).
- Mantener contrato SSR + HTMX, sin introducir SPA.

### 10.4 Punto de extensión de tools y MCP

Agregar una tool nueva no debe requerir cambios en `graph.py`:

1. Definir `ToolDefinition` (incluyendo `risk`) en catálogo.
2. Implementar handler en `TOOL_HANDLERS`.
3. Registrar wiring de integración requerido (si aplica).

Para una tool proveniente de servidor MCP se sigue el mismo patrón: catálogo + handler adapter.

## 11) Variables de entorno (alcance agent_total)

### Obligatorias

| Variable | Uso |
| --- | --- |
| `SUPABASE_URL` | URL del proyecto |
| `SUPABASE_ANON_KEY` | Cliente anon |
| `SUPABASE_SERVICE_ROLE_KEY` | Operaciones servidor |
| `DATABASE_URL` | Conexión directa Postgres para checkpointing |
| `OPENROUTER_API_KEY` | LLM/embeddings |
| `SECRET_KEY` | Firma de sesión |

### Opcionales

| Variable | Uso |
| --- | --- |
| `FILE_TOOLS_ENABLED` | Habilita file tools con fail-closed |
| `FILE_TOOLS_ROOT` | Raíz de confinamiento de archivos |
| `OAUTH_ENCRYPTION_KEY` | Reservado para integraciones futuras que requieran almacenar tokens cifrados (AES-256-GCM vía `app/db/crypto.py`); ninguna integración activa lo usa hoy |
| `LANGFUSE_PUBLIC_KEY` | Callback de trazas |
| `LANGFUSE_SECRET_KEY` | Callback de trazas |
| `LANGFUSE_HOST` | Host Langfuse |
| `EVAL_USER_ID` | Usuario de `profiles` contra el cual correr `evals/run_faq_experiment.py` manualmente; no se usa en runtime de producción |
| `ENVIRONMENT` | `development` (default) o `production`. Controla `secure`/`https_only` en cookies de sesión (`sb-access-token`, `sb-refresh-token`, cookie de `SessionMiddleware`): solo `production` activa `secure=True`. |

## 12) Estado operativo y próximos pasos

Las 15 fases de `docs/agent_total-plan.md` están en `HECHO`. No hay pendientes bloqueantes
para la plantilla en su alcance actual; lo que quedó deliberadamente fuera de alcance está
listado en `docs/agent_total-as-built.md` ("Qué quedó fuera de alcance a propósito"), no
como trabajo pendiente sino como decisión consciente de scope.

Para quien extienda esta plantilla: el punto de extensión de tools (catálogo + adapter, ver
§10.4) es el mecanismo pensado para agregar nuevas integraciones sin tocar `graph.py`.

La ejecución por fases vive en `docs/agent_total-plan.md`; el resumen consolidado y la
lección aprendida principal del proyecto viven en `docs/agent_total-as-built.md`.
