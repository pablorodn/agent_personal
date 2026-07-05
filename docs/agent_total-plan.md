# Plan Maestro - agent_total

Estado global: EN PROGRESO  
Convenciones: cada fase usa `PENDIENTE`, `EN PROGRESO` o `HECHO`.
Regla de cierre de fase (baseline): antes de iniciar una fase se registra el resultado base de `ruff check .`, `mypy app/` y `pytest -q`. Para marcar la fase como HECHO, se exige: (1) sin regresiones respecto de ese baseline, (2) los tests de aceptación de la fase en verde, (3) sin errores nuevos en los archivos tocados por la fase. Errores preexistentes ya asignados explícitamente a otra fase del plan no bloquean el cierre de la fase actual, siempre que no hayan empeorado.

---

## Fase 0 - Documentación

Estado: HECHO

Checklist:

- [x] Redefinir alcance documental a `agent_total`.
- [x] Eliminar referencias de alcance retirado en docs/rules.
- [x] Publicar plan maestro por fases.
- [x] Crear candado de documentación (`change-control.mdc`).

Criterio de aceptación:

- Documentación actualizada en `README.md`, `docs/technical-brief.md`, `docs/ui-design.md`, `.cursor/.rules/*.mdc`, `docs/agent_total-plan.md`.
- Antes de marcar esta fase como HECHO: agregar entrada correspondiente en `docs/agent_total-changelog.md` (bugs encontrados, discrepancias de spec si las hubo, resultado de `ruff check .`, `mypy app/`, `pytest -q`).

---

## Fase 1 - Migración de Supabase

Estado: HECHO

Checklist:

- [x] Crear `migrations/00006_agent_total_scope.sql`: agregar columna `profiles.default_model` (`text`, nullable).
- [x] `profiles.default_model` es texto libre sin `CHECK` constraint contra la lista curada de modelos (para no requerir migración nueva al ampliar la lista); la validación contra la lista vigente ocurre en capa de aplicación (ver Fase 10).
- [x] Mantener intactas `telegram_accounts`, `telegram_link_codes`, `scheduled_tasks`, `scheduled_task_runs`.
- [x] Documentar explícitamente que cualquier `DROP` es opcional futuro y requiere autorización explícita separada.

Criterio de aceptación (tests):

- La migración aplica limpio sobre el esquema actual.
- Existe test de compatibilidad hacia adelante y rollback razonable.
- Decisión de cierre (aplicación retroactiva de regla de baseline, autorizada explícitamente por el usuario el 2026-07-03): errores `mypy app/` preexistentes y fuera de los archivos tocados por Fase 1 no bloquean el cierre de esta fase.
- Antes de marcar esta fase como HECHO: agregar entrada correspondiente en `docs/agent_total-changelog.md` (bugs encontrados, discrepancias de spec si las hubo, resultado de `ruff check .`, `mypy app/`, `pytest -q`).

---

## Fase 2 - Entorno local y validación de conexiones

Estado: HECHO

Checklist:

- [x] Crear `.env` local a partir de `.env.example` sin variables fuera de alcance.
- [x] Implementar script `scripts/check_connections.py` ejecutable con `uv run`.
- [x] Validar Supabase REST.
- [x] Validar `DATABASE_URL` directo para checkpointer.
- [x] Validar OpenRouter con llamada mínima real a modelo económico.
- [x] Validar Langfuse cuando haya keys.

Criterio de aceptación (tests):

- El script corre y reporta `OK/FAIL` por integración.
- En fallo, el mensaje explica qué configuración falta.
- Validación real completada tras la extensión de alcance autorizada (2026-07-03): se aplicaron migraciones `00001` a `00006` en Supabase real y `scripts/check_connections.py` confirmó `all integrations OK` para `supabase_rest`, `database_url_direct`, `openrouter_chat` y `langfuse`.
- Blocker conocido no bloqueante: `pytest -q` FAIL en este host por falta de `libpq`/wrapper de `psycopg`; no corresponde a regresión de código sino a prerequisito de entorno pendiente.
- Antes de marcar esta fase como HECHO: agregar entrada correspondiente en `docs/agent_total-changelog.md` (bugs encontrados, discrepancias de spec si las hubo, resultado de `ruff check .`, `mypy app/`, `pytest -q`).

---

## Fase 3 - Reducción del catálogo de tools

Estado: HECHO

Checklist:

- [x] Quitar del código:
  - `app/routers/integrations.py`
  - `app/services/github_client.py`
  - `app/tools/bash_exec.py`
  - `schedule_task` (schemas/adapters/router cron/services relacionados)
  - `app/routers/telegram.py`
  - `app/services/telegram_bot.py`
  - `app/db/queries/telegram.py`
  - `app/db/queries/scheduled_tasks.py`
- [x] Reducir `app/tools/catalog.py` y `app/tools/adapters.py` a:
  - `get_user_preferences`
  - `list_enabled_tools`
  - `read_file`
  - `write_file`
  - `edit_file`
- [x] Eliminar campo `cron_safe` de `ToolDefinition` (sin consumidores tras remover scheduler).
- [x] Eliminar ruta muerta `GET /auth/callback` (`app/routers/auth.py`), sin flujo OAuth/magic-link en `agent_total`.
- [x] Actualizar `app/main.py` quitando routers eliminados.
- [x] Actualizar `pyproject.toml` quitando dependencias fuera de alcance y evaluar `asyncpg` antes de remover (evaluado: se mantiene `asyncpg` porque su uso vigente está en `scripts/check_connections.py`).
- [x] Actualizar o eliminar tests asociados.

Criterio de aceptación (tests):

- `ruff check .` en verde.
- `mypy app/` en verde.
- `pytest -q` en verde.
- Cero referencias a `github`, `bash`, `telegram`, `schedule_task` en `app/`.
- Decisión documentada de dependencia: `asyncpg` se evaluó y se mantiene en `pyproject.toml` por uso vigente en `scripts/check_connections.py` (fuera de `app/`, pero en alcance operativo del repo).
- Antes de marcar esta fase como HECHO: agregar entrada correspondiente en `docs/agent_total-changelog.md` (bugs encontrados, discrepancias de spec si las hubo, resultado de `ruff check .`, `mypy app/`, `pytest -q`).

---

## Fase 4 - Memoria real

Estado: HECHO

Checklist:

- [x] Implementar `memory_injection_node` real.
- [x] Embedding del último mensaje de usuario.
- [x] Invocar `match_memories` con parámetro correcto `match_user_id`.
- [x] Invocar `match_memories` con `match_count=8` (top-K fijo).
- [x] Invocar `increment_memory_retrieval_count` sobre los recuerdos efectivamente inyectados en el prompt, tras la recuperación.
- [x] Prependear `[MEMORIA DEL USUARIO]` al `system_prompt`.
- [x] Corregir mismatch en `app/db/queries/memories.py`.
- [x] Aplicar `can_store_memory()` dentro de `memory_flush.py` antes de guardar.

Criterio de aceptación (tests):

- Test con memorias existentes.
- Test sin memorias.
- Test de bloqueo de contenido sensible.
- Suite de memoria en verde.
- Antes de marcar esta fase como HECHO: agregar entrada correspondiente en `docs/agent_total-changelog.md` (bugs encontrados, discrepancias de spec si las hubo, resultado de `ruff check .`, `mypy app/`, `pytest -q`).

---

## Fase 5 - Compactación completa

Estado: HECHO

Checklist:

- [x] Implementar etapa 2 con LLM usando `create_compaction_model()`.
- [x] Resumen por secciones.
- [x] Preservar cola verbatim de `COMPACTION_TAIL_SIZE`.
- [x] Circuit breaker con `CIRCUIT_BREAKER_LIMIT`.

Criterio de aceptación (tests):

- Test de umbral de compactación.
- Test de circuit breaker.
- Test de preservación de cola reciente.
- Antes de marcar esta fase como HECHO: agregar entrada correspondiente en `docs/agent_total-changelog.md` (bugs encontrados, discrepancias de spec si las hubo, resultado de `ruff check .`, `mypy app/`, `pytest -q`).

---

## Fase 6 - Tracking y límites del runtime

Estado: HECHO

Checklist:

- [x] Enrutar todas las tools (incluyendo `low`) por `run_with_tracking`.
- [x] Aplicar `MAX_TOOL_ITERATIONS = 6` efectivamente en loop del grafo.
- [x] Si se excede `MAX_TOOL_ITERATIONS`, cortar el loop `agent->tools` de forma controlada y responder mensaje explícito al usuario (sin marcar `failed`).

Criterio de aceptación (tests):

- Test que verifica inserción en `tool_calls` para tool `low`.
- Test que verifica corte al exceder `MAX_TOOL_ITERATIONS`.
- Antes de marcar esta fase como HECHO: agregar entrada correspondiente en `docs/agent_total-changelog.md` (bugs encontrados, discrepancias de spec si las hubo, resultado de `ruff check .`, `mypy app/`, `pytest -q`).

---

## Fase 7 - Langfuse conectado

Estado: HECHO

Checklist:

- [x] Adjuntar `callbacks=[create_langfuse_callback()]` al `app.ainvoke()` en `run_agent()`.
- [x] Adjuntar metadata: `langfuse_user_id`, `langfuse_session_id`, `langfuse_tags`.
- [x] Fijar esquema de tags en runtime web: `langfuse_tags = ["agent_total", "interactive", "resume"|"message"]`.

Criterio de aceptación (tests):

- Test que verifica callback adjunto cuando hay keys.
- Test que verifica comportamiento estable sin keys.
- Antes de marcar esta fase como HECHO: agregar entrada correspondiente en `docs/agent_total-changelog.md` (bugs encontrados, discrepancias de spec si las hubo, resultado de `ruff check .`, `mypy app/`, `pytest -q`).

---

## Fase 8 - Evaluaciones reales

Estado: HECHO

Checklist:

- [x] Reescribir `evals/run_faq_experiment.py` para invocar `run_agent()` real.
- [x] Usar `evals/faq_cases.json` como entrada.
- [x] Reportar dataset run en Langfuse cuando esté configurado.

Criterio de aceptación (tests):

- Script corre contra runtime real.
- Produce score basado en respuestas reales.
- Antes de marcar esta fase como HECHO: agregar entrada correspondiente en `docs/agent_total-changelog.md` (bugs encontrados, discrepancias de spec si las hubo, resultado de `ruff check .`, `mypy app/`, `pytest -q`).

---

## Fase 9 - Adjuntos multimodales

Estado: HECHO

Checklist:

- [x] Input de archivo en formulario de chat.
- [x] Envío backend y construcción `HumanMessage` multimodal.
- [x] Soporte para imágenes y PDF.
- [x] Soporte multimodal acotado: imágenes garantizadas para ambos modelos de la lista curada; PDF en modo best-effort (si el modelo lo ignora, el turno continúa sin bloquear).
- [x] Límites de tamaño/tipo con errores claros en UI.
- [x] Persistir metadata de adjuntos en `agent_messages.structured_payload` del mensaje de usuario (ej. `{type: "attachment_note", count: N, kinds: [...]}`) sin guardar contenido binario.
- [x] Renderizar en historial indicador genérico de adjuntos (ej. `📎 Se enviaron N archivo(s)`), incluyendo recarga de sesión.
- [x] Permitir pegar imagen desde portapapeles (evento `paste` en input del chat) con los mismos límites de tipo/tamaño que el selector de archivos.

Criterio de aceptación (tests):

- Test de integración que valida armado de mensaje multimodal desde archivo simulado.
- Antes de marcar esta fase como HECHO: agregar entrada correspondiente en `docs/agent_total-changelog.md` (bugs encontrados, discrepancias de spec si las hubo, resultado de `ruff check .`, `mypy app/`, `pytest -q`).

---

## Fase 10 - Selector de modelo

Estado: HECHO

Checklist:

- [x] Selector UI con set curado de modelos OpenRouter.
- [x] Lista curada inicial fija del selector: `google/gemini-2.5-flash` y `openai/gpt-4o-mini` (única fuente de verdad hasta futura sesión dedicada de documentación).
- [x] Parametrizar `create_chat_model()` por modelo elegido.
- [x] Validar server-side el modelo recibido contra la lista curada antes de invocar `create_chat_model()`; si no está permitido, ignorar valor y usar default con warning log (sin error duro al usuario).
- [x] Persistir preferencia en `profiles.default_model` (opcional por flujo).

Criterio de aceptación (tests):

- Test que verifica propagación del modelo elegido hasta la llamada LLM.
- Antes de marcar esta fase como HECHO: agregar entrada correspondiente en `docs/agent_total-changelog.md` (bugs encontrados, discrepancias de spec si las hubo, resultado de `ruff check .`, `mypy app/`, `pytest -q`).

---

## Fase 11 - Pulido de UI

Estado: HECHO

Checklist:

- [x] Botón copiar por mensaje del asistente.
- [x] Bloques de código con `highlight.js` vía CDN.

Criterio de aceptación:

- Revisión manual documentada (sin test automatizado razonable).
- Antes de marcar esta fase como HECHO: agregar entrada correspondiente en `docs/agent_total-changelog.md` (bugs encontrados, discrepancias de spec si las hubo, resultado de `ruff check .`, `mypy app/`, `pytest -q`).

---

## Fase 12 - Punto de extensión MCP

Estado: PENDIENTE

Checklist:

- [ ] Crear scaffolding mínimo para tool de servidor MCP.
- [ ] Demostrar registro vía catálogo + adapter sin tocar `graph.py`.
- [ ] Documentar ejemplo de referencia.

Criterio de aceptación (tests):

- Documentación lista.
- Test que registra tool de ejemplo por el mismo mecanismo sin modificar `graph.py`.
- Antes de marcar esta fase como HECHO: agregar entrada correspondiente en `docs/agent_total-changelog.md` (bugs encontrados, discrepancias de spec si las hubo, resultado de `ruff check .`, `mypy app/`, `pytest -q`).

---

## Fase 13 - Sesiones: título automático, archivar y eliminar

Estado: PENDIENTE

Checklist:

- [ ] Crear `migrations/00007_sessions_title_and_archive.sql` (migración nueva e independiente): agregar columna `agent_sessions.title` (`text`, nullable, default null); extender el CHECK de `agent_sessions.status` de `('active','closed')` a `('active','archived','closed')` siguiendo el patrón `DROP CONSTRAINT IF EXISTS agent_sessions_status_check` / `ADD CONSTRAINT` ya usado en `migrations/00003`.
- [ ] `db/queries/sessions.py`: `list_sessions()` agrega `.limit(10)` además del `.order("last_used_at", desc=True)` y `.eq("status","active")`.
- [ ] Nueva función de título: generar título corto (máx. 6 palabras, sin comillas ni punto final) usando `create_compaction_model()` (no el modelo principal de chat), a partir del primer mensaje de usuario de la sesión.
- [ ] Trigger: tras cualquier turno completado sin confirmación pendiente (mismo punto donde hoy se dispara `flush_session_memory` vía `asyncio.create_task`), si `agent_sessions.title IS NULL`, disparar generación de título en background (fire-and-forget, no bloquea respuesta). Debe poder reintentarse en turnos siguientes si falla (condición de disparo: `title IS NULL`).
- [ ] Persistencia: `UPDATE agent_sessions SET title = ... WHERE id = session_id AND title IS NULL` (guard de idempotencia ante condición de carrera).
- [ ] Manejo de fallos: mismo patrón que `memory_flush.py` (`try/except`, warning log, nunca rompe el turno). Mientras no haya título, la UI mantiene fallback por fecha (`format_session_date`).
- [ ] Nuevas rutas: `POST /api/sessions/{id}/archive` y `POST /api/sessions/{id}/delete`.
  - `archive`: valida ownership, `UPDATE status='archived'`. Si `session_id` coincide con `current_session_id` del request, crea sesión nueva vacía y responde `HX-Redirect: /chat`; si no coincide, responde partial vacío para remover item.
  - `delete`: valida ownership, hard-delete real (`DELETE FROM agent_sessions WHERE id=...`; cascada vía `ON DELETE CASCADE` de `migrations/00001` para `agent_messages` y `tool_calls`). Si es sesión actual: crea sesión nueva + `HX-Redirect: /chat`; si no: partial vacío para remover item.
- [ ] Confirmación en UI: botón "Eliminar" usa `hx-confirm` con mensaje claro; botón "Archivar" no requiere confirmación.
- [ ] Menú de 3 puntos: función JS inline `toggleSessionMenu(id)` en `chat.html`, sin click-outside-to-close en esta fase (limitación aceptada y documentada).
- [ ] Al ejecutar hard-delete de una sesión en `POST /api/sessions/{id}/delete`, además de `DELETE FROM agent_sessions`, eliminar el estado del checkpointer de LangGraph asociado a ese `thread_id` (`session_id`) para que no quede historial recuperable en tablas internas de `AsyncPostgresSaver`. Verificar en implementación si la versión instalada de `langgraph-checkpoint-postgres` expone método de borrado de hilo (`adelete_thread` o equivalente); si no existe API, documentar ausencia y hacer `DELETE` manual sobre tablas de checkpoint filtrando por `thread_id`, en la misma operación lógica. Best-effort: si falla limpieza del checkpointer, no bloquear borrado de `agent_sessions`; sí registrar warning.
- [ ] Fuera de alcance de esta fase: no construir pantalla de archivados ni recuperación; archivar solo oculta de sidebar y deja `status='archived'` en base.

Criterio de aceptación (tests):

- Tests de integración para límite de 10 sesiones, orden descendente por `last_used_at`, fallback visual cuando `title` es null, rutas `archive/delete` con ownership y comportamiento de sesión actual vs no actual.
- Test unitario/integración para generación idempotente de título (`title IS NULL`) y tolerancia a fallos sin romper turno.
- Antes de marcar esta fase como HECHO: agregar entrada correspondiente en `docs/agent_total-changelog.md` (bugs encontrados, discrepancias de spec si las hubo, resultado de `ruff check .`, `mypy app/`, `pytest -q`).

---

## Fase 14 - Cierre y hardening

Estado: PENDIENTE

Checklist:

- [ ] Migrar `@app.on_event("startup")` a lifespan.
- [ ] Limpiar los 3 `unused type: ignore` reportados por mypy.
- [ ] `secure=True` condicional por entorno en cookies.
- [ ] Documentar formalmente `POST /api/chat/stream` en brief y UI.

Criterio de aceptación (tests):

- `ruff check .` en verde.
- `mypy app/` en verde.
- `pytest -q` en verde.
- Antes de marcar esta fase como HECHO: agregar entrada correspondiente en `docs/agent_total-changelog.md` (bugs encontrados, discrepancias de spec si las hubo, resultado de `ruff check .`, `mypy app/`, `pytest -q`).

---

## Fase 15 - Consolidación de plantilla

Estado: PENDIENTE

Checklist:

- [ ] Confirmar que las 14 fases anteriores (0-14) están en HECHO.
- [ ] Revisar `docs/agent_total-changelog.md` completo: verificar que toda discrepancia de spec registrada ahí quedó efectivamente reflejada en la documentación congelada vigente (`README.md`, `technical-brief.md`, `ui-design.md`) - es decir, que ninguna decisión tomada durante la implementación quedó como "solo en el changelog" sin sincronizarse con la fuente de verdad.
- [ ] Si se encuentra alguna discrepancia sin sincronizar: esta es la única sesión donde se autoriza corregir documentación fuera de una "sesión dedicada" ad-hoc individual, porque es en sí misma la sesión dedicada de cierre. Aplicar las correcciones necesarias.
- [ ] Producir un resumen "as-built" corto (puede vivir al final de este mismo plan o como sección nueva en `README.md`): qué se construyó realmente, qué quedó fuera de alcance a propósito, y dónde está el changelog completo para quien reutilice este repo como plantilla.
- [ ] Confirmar suite completa en verde una última vez: `ruff check .`, `mypy app/`, `pytest -q`.

Criterio de aceptación:

- Documentación y changelog coherentes entre sí, sin deriva silenciosa.
- Repo queda en estado reutilizable como plantilla base para agregar nuevas herramientas/integraciones (MCP u otras) sin arqueología previa.
- Antes de marcar esta fase como HECHO: agregar entrada correspondiente en `docs/agent_total-changelog.md` (bugs encontrados, discrepancias de spec si las hubo, resultado de `ruff check .`, `mypy app/`, `pytest -q`).

