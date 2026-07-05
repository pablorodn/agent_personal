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
- Chat web multi-sesión con sidebar.
- Runtime LangGraph con grafo `memory_injection -> compaction -> agent -> tools`.
- Checkpointing con `AsyncPostgresSaver`.
- HITL genérico con `interrupt()` y `Command(resume=...)`, usando doble ID (`tool_calls.id` y `model_tool_call_id`).
- File tools con `FILE_TOOLS_ENABLED` y confinamiento de paths.
- Estructura de catálogo/política de riesgo como mecanismo central.

### Pendiente o incompleto hoy (debe quedar explícito)

- Compactación: existe implementación parcial; hoy solo está activa la etapa 1.
- Memoria de largo plazo end-to-end: la especificación completa existe, pero `memory_injection_node` actualmente es no-op.
- Recuperación vectorial: `match_memories()` hoy no se invoca en el flujo real.
- Mismatch conocido: en código se usa `query_user_id`, mientras que el RPC de `migrations/00004_long_term_memory.sql` espera `match_user_id`.
- Langfuse: existe helper para callback, pero `create_langfuse_callback()` no está conectado al `invoke` del grafo.
- Evaluaciones: `evals/run_faq_experiment.py` es un stub y no usa el runtime real.

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
| `POST /api/chat/confirm` | API | Partial de respuesta final |
| `GET /api/sessions` | API | JSON de sesiones |
| `POST /api/sessions` | API | Partial de item de sesión |
| `POST /api/sessions/{id}/clear` | API | String vacío |
| `POST /api/sessions/{id}/archive` | API | `HX-Redirect: /chat` (si archiva la sesión actual) o partial vacío para remover item |
| `POST /api/sessions/{id}/delete` | API | `HX-Redirect: /chat` (si elimina la sesión actual) o partial vacío para remover item |

### Capacidades objetivo nuevas en rutas

- Adjuntos multimodales en chat desde `/chat` y `POST /api/chat`.
- Selector de modelo en chat (`POST /api/chat`) persistiendo preferencia de usuario en `profiles.default_model`.
- Documentar formalmente `POST /api/chat/stream` en fase de cierre/hardening.

### Sesiones: título automático, archivar y eliminar (plan Fase 13)

Cambios de datos definidos para `migrations/00007_sessions_title_and_archive.sql` (Fase 13 del plan, migración independiente):

- Agregar `agent_sessions.title` (`text`, nullable, default `null`).
- Ampliar `agent_sessions.status` para aceptar `archived` además de `active` y `closed`.
- El ajuste del CHECK se hace con patrón `DROP CONSTRAINT IF EXISTS ...` + `ADD CONSTRAINT ...`.

Flujo de generación de título:

- Se usa `create_compaction_model()` para proponer un título corto (máx. 6 palabras, sin comillas ni punto final) desde el primer mensaje de usuario.
- Trigger de ejecución: tras turnos completados sin confirmación pendiente, en el mismo punto de fire-and-forget donde corre `flush_session_memory`, solo si `agent_sessions.title IS NULL`.
- Idempotencia: persistir con `UPDATE ... WHERE id = session_id AND title IS NULL`.
- Fallos: patrón `try/except` con warning log; nunca rompe el turno de chat.
- Fallback UI: mientras `title` sea `NULL`, la sidebar sigue mostrando fecha formateada (`format_session_date`).
- El hard-delete también elimina el estado persistido del checkpointer de LangGraph para ese `thread_id`; el archivado (`/archive`) NO afecta el estado del checkpointer.

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

- `memory_injection_node` es no-op.
- `match_memories()` no se invoca.
- Hay mismatch de parámetros:
  - código: `query_user_id`
  - RPC esperado: `match_user_id` (según `migrations/00004_long_term_memory.sql`)

## 9) Langfuse y evaluaciones

Objetivo:

- Conectar callback y metadata al `app.ainvoke()` del runtime:
  - `langfuse_user_id`
  - `langfuse_session_id`
  - `langfuse_tags`
  - `langfuse_tags = ["agent_total", "interactive", "resume"|"message"]` (sin variante `cron` mientras el canal activo sea web)
- Evaluaciones automáticas contra runtime real.

Estado real actual:

- `create_langfuse_callback()` existe pero no se usa en el invoke del grafo.
- `evals/run_faq_experiment.py` es stub y no invoca al agente real.

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

## 12) Estado operativo y próximos pasos

Pendientes principales para la etapa:

- Reducir el catálogo de tools al set mínimo de `agent_total`.
- Completar memoria real e inyección.
- Completar compactación etapa 2.
- Conectar Langfuse al invoke real.
- Reemplazar evaluaciones stub por evaluaciones reales.
- Incorporar adjuntos multimodales y selector de modelo.
- Añadir scaffolding de extensión MCP sin tocar el runtime del grafo.

La ejecución por fases vive en `docs/agent_total-plan.md`.
