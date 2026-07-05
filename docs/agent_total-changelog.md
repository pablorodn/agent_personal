# Changelog de ejecución - agent_total

> Registro append-only de lo que realmente pasó durante la implementación
> por fases. Este archivo NO cae bajo el candado de
> `.cursor/.rules/change-control.mdc`: se puede escribir en cualquier
> momento, incluso durante sesiones de implementación de fase. Nunca se
> edita retroactivamente lo ya escrito, solo se agrega al final.
>
> Cada entrada de fase debe registrar, como mínimo:
> - Fecha.
> - Bugs de código encontrados y corregidos durante la fase (root cause +
>   fix, en una línea cada uno). Esto NO requiere sesión de documentación:
>   es implementación normal cumpliendo una spec ya aprobada.
> - Si hubo alguna discrepancia entre lo documentado y lo que la prueba
>   reveló como correcto/necesario: qué se bloqueó, qué sesión de
>   documentación dedicada se activó, qué archivo y sección cambiaron, y
>   fecha de esa sesión. Si no hubo ninguna, decirlo explícitamente
>   ("sin discrepancias de spec").
> - Resultado final de `ruff check .`, `mypy app/`, `pytest -q` al cerrar
>   la fase.

---

## Fase 0 - Documentación

(Sin entradas de ejecución: esta fase fue puramente documental, no aplica
el formato de bugs/tests de arriba.)

## Fase 1 - Migración de Supabase

- Fecha: 2026-07-03.
- Bugs encontrados/corregidos:
  - No se detectaron bugs de código en el alcance de la migración 00006.
- Discrepancias de spec:
  - Sin discrepancias de spec.
- Resultado de validaciones al cierre del intento de fase:
  - `ruff check .`: OK (verde).
  - `mypy app/`: FAIL (4 errores preexistentes fuera del alcance de Fase 1: `app/config.py`, `app/agent/model.py`, `app/services/scheduler.py`).
  - `pytest -q tests/unit/test_migration_00006_scope.py`: OK (2 passed).

## Sesión dedicada de documentación - archivo de continuidad

- Fecha: 2026-07-03.
- Motivo que activó la sesión: necesidad explícita del usuario de crear una guía para retomar `agent_total` en sesiones nuevas sin depender de memoria conversacional.
- Autorización: explícita en el prompt del usuario ("Sesión de documentación dedicada (autorización explícita del usuario). Crear archivo nuevo docs/agent_total-resume.md, sin tocar ningún otro archivo.").
- Archivo creado/cambiado en esa sesión: `docs/agent_total-resume.md` (creado).
- Verificación posterior de esa sesión: sin cambios adicionales aplicados por instrucción en esa interacción; el resto de diffs del working tree corresponde a sesiones previas/otras tareas.

## Fase 2 - Entorno local y validación de conexiones

- Fecha: 2026-07-03.
- Bugs encontrados/corregidos:
  - `scripts/check_connections.py` inicialmente falló `ruff` por import desde `typing` (`UP035`); fix: mover `Awaitable`/`Callable` a `collections.abc`.
- Discrepancias de spec:
  - Sin discrepancias de spec.
- Resultado de validaciones:
  - Baseline (comandos literales solicitados): `ruff check .` / `mypy app/` / `pytest -q` no disponibles por PATH (`command not found`).
  - Baseline técnico previo a cambios (`python3 -m ...`): `ruff` OK, `mypy` con 4 errores (`unused-ignore` + stubs de `croniter`), `pytest` con errores de import por dependencias no instaladas.
  - Final de fase (entorno `uv`): `ruff` OK, `mypy app/` OK, `pytest -q` FAIL por ausencia de wrapper/libpq para `psycopg` en este host.
  - `scripts/check_connections.py` ejecutado con `.env` placeholder: 4 FAIL esperados por variables faltantes (`SUPABASE_*`, `DATABASE_URL`, `OPENROUTER_API_KEY`, `LANGFUSE_*`), con mensajes explícitos de configuración faltante.

## Fase 2 - Extensión autorizada: aplicación de migraciones reales en Supabase

- Fecha: 2026-07-03.
- Autorización explícita del usuario en esta fase para aplicar migraciones `00001` a `00006` contra el Supabase real configurado en `.env`.
- Verificación previa: esquema `public` vacío (`PUBLIC_TABLES: <none>`), por lo que se procedió a aplicar en orden.
- Migraciones aplicadas con éxito (en secuencia y sin errores):
  - `00001_initial_schema.sql`
  - `00002_session_management.sql`
  - `00003_scheduled_tasks.sql`
  - `00004_long_term_memory.sql`
  - `00005_tool_call_model_id.sql`
  - `00006_agent_total_scope.sql`
- Resultado posterior de `scripts/check_connections.py` con variables reales exportadas desde `.env`:
  - `supabase_rest`: OK
  - `database_url_direct`: OK
  - `openrouter_chat`: OK
  - `langfuse`: OK
  - `Summary: all integrations OK.`

## Fase 3 - Reducción del catálogo de tools

- Fecha: 2026-07-03.
- Bugs encontrados/corregidos:
  - `pytest -q` no corría por entorno sin wrapper de `psycopg`/`libpq`; fix aplicado en host: instalación de `libpq` (`brew install libpq`) + `psycopg-binary` en `.venv`, quedando la suite ejecutable.
  - Regresión de tests tras poda de alcance (`/auth/callback` eliminado y monkeypatches de integración obsoletos); fix: actualización/eliminación de tests afectados para reflejar alcance `agent_total`.
- Discrepancias de spec:
  - Sin discrepancias de spec.
- Resultado de validaciones:
  - Baseline de fase (previo a cambios de código): `ruff check .` OK, `mypy app/` OK, `pytest -q` OK (`49 passed`).
  - Final de fase: `ruff check .` OK, `mypy app/` OK, `pytest -q` OK (`38 passed`).
  - Verificación de alcance en `app/` (`rg -n -i "github|bash|telegram|schedule_task" app/`): sin coincidencias.

## Fase 4 - Memoria real

- Fecha: 2026-07-03.
- Bugs encontrados/corregidos:
  - Mismatch RPC en `app/db/queries/memories.py`: el código enviaba `query_user_id` pero `match_memories` en `migrations/00004_long_term_memory.sql` espera `match_user_id`; fix: payload RPC corregido a `match_user_id`.
  - `memory_injection_node` era no-op; fix: embedding del último mensaje de usuario, recuperación con `match_count=8`, prepend de `[MEMORIA DEL USUARIO]`, e incremento con `increment_memory_retrieval_count` sobre recuerdos inyectados.
  - `memory_flush.py` persistía sin filtro de privacidad; fix: gate con `can_store_memory()` antes de guardar.
- Discrepancias de spec:
  - Sin discrepancias de spec.
- Resultado de validaciones:
  - Baseline de fase (previo a cambios de código): `ruff check .` OK, `mypy app/` OK, `pytest -q` OK (`38 passed`).
  - Final de fase: `ruff check .` OK, `mypy app/` OK, `pytest -q` OK (`42 passed`).
  - Tests de aceptación de memoria: con memorias existentes, sin memorias, bloqueo de contenido sensible, y RPC con `match_user_id`.

## Fase 5 - Compactación completa

- Fecha: 2026-07-03.
- Bugs encontrados/corregidos:
  - `compaction_node` devolvía `{"messages": microcompact(...)}` sobre un estado con reducer `add_messages`, lo que appendeaba en lugar de reemplazar; fix: `RemoveMessage(id=REMOVE_ALL_MESSAGES)` + mensajes compactados.
- Discrepancias de spec:
  - `CIRCUIT_BREAKER_LIMIT` aparece en `docs/technical-brief.md` §7 sin valor numérico; se introdujo la constante en `app/agent/compaction.py` con valor `3` (pendiente de confirmación del usuario para cierre de fase).
  - "Resumen por secciones" no define nombres concretos en la spec; implementación usa cuatro secciones markdown fijas en el prompt: `## Contexto`, `## Acciones y herramientas`, `## Decisiones y resultados`, `## Pendiente`.
  - Interacción etapa 1 / etapa 2: al superar umbral se intenta etapa 2 (`llm_compact`); ante fallo LLM se hace fallback a etapa 1 (`microcompact`); con `compaction_failure_count >= CIRCUIT_BREAKER_LIMIT` se omite LLM y solo aplica etapa 1.
- Resultado de validaciones:
  - Baseline de fase (previo a cambios de código): `ruff check .` OK, `mypy app/` OK, `pytest -q` OK (`42 passed`).
  - Final de fase: `ruff check .` OK, `mypy app/` OK, `pytest -q` OK (`47 passed`).
  - Tests de aceptación de compactación: umbral (`test_should_compact_respects_threshold`), circuit breaker (`test_compaction_node_circuit_breaker_skips_llm_after_limit`), preservación de cola reciente (`test_llm_compact_preserves_recent_tail`, `test_microcompact_preserves_recent_tail`).

## Sesión dedicada de documentación - compactación §7

- Fecha: 2026-07-03.
- Motivo que activó la sesión: spec incompleta detectada durante Fase 5 — `CIRCUIT_BREAKER_LIMIT` sin valor numérico, interacción etapa 1/etapa 2 no documentada, y formato de secciones del resumen LLM sin nombres concretos; valores confirmados por el usuario tras revisión de la implementación (coinciden con código, sin cambio de código).
- Autorización: explícita en el prompt del usuario (verificación y completar documentación en `docs/technical-brief.md` §7; no marcar Fase 5 como HECHO).
- Archivo/sección cambiados: `docs/technical-brief.md` §7 (Compactación de contexto) — añadidos `CIRCUIT_BREAKER_LIMIT = 3`, flujo etapa 2 → fallback etapa 1 / circuit breaker, y secciones markdown fijas del resumen.

## Fase 6 - Tracking y límites del runtime

- Fecha: 2026-07-03.
- Bugs encontrados/corregidos:
  - Tools `low` ejecutaban handler directo sin persistir en `tool_calls`; fix: ruta por `run_with_tracking()` en `tool_executor_node`.
  - `MAX_TOOL_ITERATIONS` existía como constante pero no se aplicaba en el grafo; fix: contador `tool_iteration_count` en `AgentState`, incremento post-`tools`, nodo `limit_reached` y rama condicional en `should_continue`.
- Discrepancias de spec:
  - Texto y estado al exceder límite no estaban en el plan; el usuario confirmó en sesión: mensaje *"Alcancé el límite de 6 iteraciones de herramientas para este turno. Respondo con lo obtenido hasta ahora; si necesitás más pasos, enviá otro mensaje."* y conservar el último `AIMessage` con `tool_calls` sin ejecutar, agregando un `AIMessage` final de límite (sin marcar `failed`).
  - Tools `medium/high` siguen usando tracking HITL vía `find_or_create_pending_tool_call` (no duplicar registro con `run_with_tracking`); el checklist enfatiza `low`, que era el gap.
- Resultado de validaciones:
  - Baseline de fase (previo a cambios de código): `ruff check .` OK, `mypy app/` OK, `pytest -q` OK (`47 passed`).
  - Final de fase: `ruff check .` OK, `mypy app/` OK, `pytest -q` OK (`50 passed`).
  - Tests de aceptación: inserción en `tool_calls` para tool `low` (`test_low_tool_execution_inserts_tool_call_record`), corte al exceder `MAX_TOOL_ITERATIONS` (`test_should_continue_routes_to_limit_when_max_iterations_exceeded`, `test_limit_reached_preserves_unexecuted_tool_calls_and_adds_limit_message`).

## Sesión dedicada de documentación - límites de runtime (§5)

- Fecha: 2026-07-03.
- Motivo que activó la sesión: spec incompleta detectada durante Fase 6 — la sección "Límites de ejecución del runtime" en `docs/technical-brief.md` no contenía el texto exacto del mensaje al usuario ni el comportamiento de estado al cortar por `MAX_TOOL_ITERATIONS`; valores confirmados por el usuario tras revisión de la implementación (coinciden con código, sin cambio de código).
- Autorización: explícita en el prompt del usuario (verificación Parte A / completar documentación en `docs/technical-brief.md`; no marcar Fase 6 como HECHO).
- Archivo/sección cambiados: `docs/technical-brief.md` §5 — subsección "Límites de ejecución del runtime" — añadidos texto exacto de `MAX_TOOL_ITERATIONS_LIMIT_MESSAGE` y comportamiento de estado (`AIMessage` con `tool_calls` sin ejecutar + `AIMessage` final de límite; `run_agent` devuelve el último mensaje).

## Fase 7 - Langfuse conectado

- Fecha: 2026-07-03.
- Bugs encontrados/corregidos:
  - Import eager de `langfuse.langchain.CallbackHandler` en `app/agent/langfuse.py` rompía import de `app.agent.graph` al exigir paquete `langchain` (el proyecto usa `langchain-core`); fix: import lazy dentro de `create_langfuse_callback()`.
- Discrepancias de spec:
  - Sin discrepancias de spec. Criterio `resume`|`message`: `run_agent()` ya distingue invocaciones vía `bool(agent_input.resume_decision)` — `None`/falsy → tag `"message"`; HITL `Command(resume=...)` → tag `"resume"`.
- Resultado de validaciones:
  - Baseline de fase (previo a cambios de código): `ruff check .` OK, `mypy app/` OK, `pytest -q` OK (`50 passed`).
  - Final de fase: `ruff check .` OK, `mypy app/` OK, `pytest -q` OK (`57 passed`).
  - Tests de aceptación: callback adjunto cuando hay keys (`test_augment_invoke_config_attaches_callback_when_keys_present`, `test_run_agent_passes_langfuse_config_on_message`); comportamiento estable sin keys (`test_augment_invoke_config_stable_without_keys`, `test_run_agent_uses_resume_tag_for_hitl_resume`).

## Fase 8 - Evaluaciones reales

- Fecha: 2026-07-03.
- Bugs encontrados/corregidos:
  - No se detectaron bugs de código fuera del alcance del stub previo.
- Discrepancias de spec:
  - Sin discrepancias de spec. Scoring: se reutilizó la lógica preexistente del stub (`expected_keywords` → ratio de hits en la respuesta, case-insensitive); solo se reemplazó la respuesta simulada por salida real de `run_agent()`.
  - Ejecución manual del script requiere `EVAL_USER_ID` (UUID de `profiles.id`); documentado en mensaje de error del script y en `.env.example`.
- Resultado de validaciones:
  - Baseline de fase (previo a cambios de código): `ruff check .` OK, `mypy app/` OK, `pytest -q` OK (`57 passed`).
  - Final de fase: `ruff check .` OK, `mypy app/` OK, `pytest -q` OK (`62 passed`).
  - Tests de aceptación: runtime real vía `run_agent()` (`test_answer_case_invokes_run_agent`); score sobre respuestas reales (`test_score_case_uses_keyword_hits_in_real_answer`, `test_run_faq_eval_without_langfuse_uses_real_answers`); Langfuse dataset run cuando hay keys (`test_run_faq_eval_reports_langfuse_dataset_run_when_configured`).

## Sesión dedicada de documentación - EVAL_USER_ID (§11)

- Fecha: 2026-07-03.
- Motivo que activó la sesión: `EVAL_USER_ID` agregada a `.env.example` durante Fase 8 pero ausente en `docs/technical-brief.md` §11; aclaración del usuario antes de cerrar la fase.
- Autorización: explícita en el prompt del usuario (verificar necesidad de `EVAL_USER_ID` y completar §11; no marcar Fase 8 como HECHO).
- Archivo/sección cambiados: `docs/technical-brief.md` §11 (Variables de entorno) — añadida fila `EVAL_USER_ID` en opcionales con propósito de eval manual.

## Fase 9 - Adjuntos multimodales (intento, sin cerrar como HECHO)

- Fecha: 2026-07-05.
- Valores no fijados por el checklist, confirmados explícitamente por el usuario antes de implementar (coinciden con los ya escritos en `docs/ui-design.md` §6, verificados durante la implementación):
  - Límites: imagen ≤5 MB (`image/png`, `image/jpeg`, `image/webp`); PDF ≤10 MB (`application/pdf`); máximo 3 adjuntos por mensaje.
  - Aviso de PDF ignorado por el modelo en modo best-effort: completamente silencioso (sin indicio adicional más allá del indicador genérico de adjuntos).
  - `structured_payload.kinds`: lista de tipos únicos presentes (ej. `["image","pdf"]`), sin campos adicionales fuera de `type`/`count`/`kinds`.
  - Texto del indicador: literal `📎 Se enviaron N archivo(s)` para cualquier N, sin variación singular/plural.
  - Mensaje de texto vacío con adjuntos: se permite enviar el turno solo con adjuntos (se relajó la validación existente que exigía texto siempre).
- Bugs encontrados/corregidos (dentro del alcance de esta fase):
  - Ninguno preexistente en el código tocado; los únicos ajustes fueron los de tipado detectados por `mypy` durante la propia implementación (invariancia de `list[dict]` al usar `create_image_block`/`create_file_block` de `langchain_core` y al construir `HumanMessage(content=parts)`), resueltos con `dict(...)` y anotación `list[str | dict[Any, Any]]` respectivamente.
- Discrepancias de spec: sin discrepancias de spec (los 5 valores no fijados por el checklist fueron confirmados con el usuario antes de escribir código; no requirieron modificar documentación congelada).
- Hallazgos fuera de alcance de esta fase (no corregidos, solo reportados por instrucción explícita de no tocar código fuera del alcance autorizado):
  - `app/templates/chat.html`: en `submitChat()`, `renderOutgoingMessage(form)` limpia `#chat-input` (`input.value = ""`) *antes* de que `new FormData(form)` se construya en la línea siguiente. Esto es previo a esta fase y no relacionado con adjuntos; con el diseño actual de adjuntos se evitó reproducir el mismo problema (el reset de adjuntos ocurre recién después de construir `FormData`, vía `resetAttachmentsUI()` tras la línea `const formData = new FormData(form)`).
  - El contenido base64 de los adjuntos queda embebido en el `HumanMessage` que LangGraph persiste vía `AsyncPostgresSaver` (checkpointer), igual que el resto de la conversación. El checklist de esta fase dice "sin persistencia de adjuntos" pero eso se interpretó — y así lo confirmó el flujo de preguntas — como alcance de `agent_messages.structured_payload` (sin contenido binario en esa tabla), no como ausencia total de bytes en Postgres vía el checkpointer, que ya persiste el resto del historial de mensajes de todas las fases previas.
  - `app/agent/nodes/memory_injection_node.py` (Fase 4, no tocado): `_last_user_message_content()` exige `isinstance(content, str)`; cuando un turno es solo-adjuntos (contenido tipo lista), la inyección de memoria se omite para ese turno (comportamiento fail-open ya existente, no una falla nueva).
  - `docs/ui-design.md` §5/§11 documenta `POST /api/chat` como ruta de envío de chat con adjuntos, pero la UI real (`chat.html`) envía por `POST /api/chat/stream` (discrepancia preexistente, ya señalada para Fase 14). Se implementó soporte de adjuntos en ambos endpoints (`/api/chat` y `/api/chat/stream`) para no dejar el contrato documentado sin cobertura, sin cambiar cuál usa la UI.
  - Partial `partials/chat_attachment_errors.html` sugerido como "o equivalente" en `docs/ui-design.md` §10: se implementó como `<p id="attachment-error">` gestionado por JS inline en `chat.html`, no como partial Jinja separado.
- Verificación manual de UI: no se ejecutó en navegador real (evitado para no generar mensajes reales contra el Supabase/OpenRouter de producción configurados en `.env`). Se verificó en su lugar: sintaxis del bloque `<script>` de `chat.html` con `node --check` (OK), y el renderizado Jinja real de `chat.html`/`message.html` a través de los tests existentes que hacen `GET /chat` (pasan sin error de plantilla).
- Resultado de validaciones:
  - Baseline de fase (previo a cambios de código): `ruff check .` OK, `mypy app/` OK (51 archivos), `pytest -q` OK (`62 passed`).
  - Final de fase: `ruff check .` OK, `mypy app/` OK (52 archivos), `pytest -q` OK (`79 passed`).
  - Tests de aceptación: `tests/unit/test_attachments.py` (validación de tipo/tamaño/cantidad y construcción de content blocks), `tests/unit/test_agent_multimodal.py` (armado de `HumanMessage` multimodal, incluido `test_run_agent_passes_multimodal_content_to_graph`), `tests/integration/test_chat_attachments.py` (adjunto simulado end-to-end vía `POST /api/chat`, mensaje solo-adjuntos, rechazo por tamaño/tipo/cantidad sin persistir mensaje).
- Fase NO marcada como HECHO por instrucción explícita del usuario; queda en estado `EN PROGRESO` en `docs/agent_total-plan.md` con el checklist tildado.

## Sesión dedicada de documentación - adjuntos §10.1/§6 (texto opcional con adjuntos)

- Fecha: 2026-07-05.
- Motivo que activó la sesión: durante la Fase 9 se tomó una decisión de spec no registrada en la documentación congelada — se relajó la validación existente que exigía mensaje de texto siempre, para permitir enviar un turno solo con adjuntos y sin texto acompañante; el valor fue confirmado explícitamente por el usuario antes de implementar, pero no había quedado reflejado en `docs/technical-brief.md` ni en `docs/ui-design.md`.
- Autorización: explícita en el prompt del usuario ("Parte A — Sesión de documentación dedicada (autorización explícita del usuario)"; no marcar Fase 9 como HECHO en ese paso).
- Archivo/sección cambiados:
  - `docs/technical-brief.md` §10.1 (Adjuntos multimodales en chat) — añadida línea "El mensaje de texto es opcional cuando el turno incluye adjuntos: se permite enviar solo adjuntos sin texto acompañante." junto a los límites existentes.
  - `docs/ui-design.md` sección 6 (Adjuntos multimodales) — añadida la misma línea junto a "Límites de la etapa".
- Cierre de Fase 9 (Parte B, 2026-07-05): con la documentación ya sincronizada, se re-ejecutó `ruff check .` (OK), `mypy app/` (OK, 52 archivos) y `pytest -q` (OK, `79 passed`) — mismo resultado que el "Final de fase" ya reportado, sin regresiones. Fase 9 cierra sin discrepancias de spec pendientes; `docs/agent_total-plan.md` pasa de `EN PROGRESO` a `HECHO`.
