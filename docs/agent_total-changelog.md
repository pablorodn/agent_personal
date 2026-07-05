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

## Fase 10 - Selector de modelo (intento, sin cerrar como HECHO)

- Fecha: 2026-07-05.
- Baseline de fase (previo a cambios de código): `ruff check .` OK, `mypy app/` OK (52 archivos), `pytest -q` OK (`79 passed`) — coincide con el "Final de fase" reportado al cierre de Fase 9.
- Valores no fijados por el checklist, confirmados explícitamente por el usuario antes de implementar:
  - Default de la validación server-side cuando el modelo recibido no está permitido: siempre `PRIMARY_CHAT_MODEL` (`google/gemini-2.5-flash`, primer elemento de la lista curada), sin importar si el usuario ya tenía otro `profiles.default_model` guardado.
  - Persistencia de `profiles.default_model`: automática al cambiar el selector (preferencia global de cuenta, sobrescribe la anterior), tanto desde `/settings` como desde el selector del formulario de chat.
  - Ubicación del selector: ambos — un `<select>` en `/settings` (define el default de cuenta) y otro dentro del formulario de chat en `chat.html` (permite override en el momento; el envío del turno persiste ese valor como nuevo default si difiere del guardado).
  - Formato del warning log al ignorar un modelo no permitido: log estructurado (`logger.warning` con `extra`), evento `model_selection_rejected`, incluyendo `requested_model`, `fallback_model` y `user_id`. Se reutiliza el mismo evento tanto para la validación en el envío de chat como para un intento de guardar un valor inválido desde `/settings`.
  - Revalidación de `profiles.default_model` ya persistido: sí, con el mismo mecanismo (`validate_model_selection()`) en cada lectura (`GET /settings`, `GET /chat`, y en cada `POST` de chat antes de invocar `create_chat_model()`), sin reescribir el valor guardado si queda obsoleto por un cambio futuro de la lista curada.
  - Interacción del modelo elegido con el fallback automático por error ya existente (`ainvoke_chat_with_fallback`): el modelo elegido pasa a ser el "primary" de esa resiliencia; si falla en runtime, cae automáticamente al otro modelo de la lista curada (comportamiento simétrico, dado que la lista curada tiene exactamente 2 elementos).
- Decisión de implementación no cubierta explícitamente por el checklist ni por las preguntas de alcance (aplicada por consistencia mínima con lo ya confirmado, documentada aquí en vez de asumida en silencio): en `POST /settings`, un `default_model` fuera de la lista curada se ignora (no se agrega al payload de `upsert_profile`, dejando intacto el valor previamente guardado) en lugar de sobrescribirlo con el default; esto evita corromper la preferencia ya guardada por un envío inválido (solo alcanzable evitando el `<select>` de la UI, ya que este último solo ofrece las 2 opciones curadas).
- Bugs encontrados/corregidos: ninguno preexistente en el código tocado. Ajuste propio detectado por `mypy` durante la implementación: un `# type: ignore[return-value]` inicial en `validate_model_selection()` resultó innecesario (mypy ya angosta `str | None` vía el chequeo `in` contra `CURATED_CHAT_MODELS: tuple[str, str]`); se removió.
- Discrepancias de spec: sin discrepancias de spec (todos los valores no fijados fueron confirmados con el usuario antes de escribir código).
- Archivos tocados: `app/agent/model.py` (`CURATED_CHAT_MODELS`, `validate_model_selection()`, `ainvoke_chat_with_fallback()` parametrizado por `primary_model`), `app/agent/state.py` y `app/agent/graph.py` (`chat_model` propagado por `AgentState`/`AgentInput`/`agent_node`), `app/db/queries/profiles.py` (campo `default_model` en `Profile`), `app/pages/settings.py` y `app/templates/settings.html` (selector + guardado), `app/pages/chat.py` y `app/templates/chat.html` (selector en el form de chat), `app/routers/chat.py` (resolución/validación/persistencia automática en `/api/chat` y `/api/chat/stream`).
- Resultado de validaciones:
  - Final de fase: `ruff check .` OK, `mypy app/` OK (52 archivos), `pytest -q` OK (`96 passed`).
  - Tests de aceptación (propagación del modelo elegido hasta la llamada LLM): `tests/unit/test_model_selection.py` (`validate_model_selection` con modelo válido/inválido/`None`, `ainvoke_chat_with_fallback` propaga `primary_model` a `create_chat_model()` y usa el otro modelo curado como fallback ante error, `agent_node` propaga `state["chat_model"]`), `tests/integration/test_chat_model_selection.py` (propagación end-to-end desde el form HTTP hasta `AgentInput.chat_model` en `POST /api/chat`, rechazo de modelo desconocido con warning y fallback a `PRIMARY_CHAT_MODEL`, persistencia automática de `_resolve_chat_model()` solo cuando el valor cambia), `tests/integration/test_settings_routes.py` (selector muestra el valor guardado, revalida un valor obsoleto en `GET /settings`, guarda un modelo válido e ignora uno inválido sin sobrescribir en `POST /settings`).
- Fase NO marcada como HECHO por instrucción explícita del usuario; queda en estado `EN PROGRESO` en `docs/agent_total-plan.md` con el checklist tildado.
- Confirmación explícita del usuario en el chat de planificación (no solo durante la sesión de implementación) sobre la persistencia automática global del selector; fase cierra sin discrepancias pendientes.

## Fase 11 - Pulido de UI (intento, sin cerrar como HECHO)

- Fecha: 2026-07-05.
- Baseline de fase (previo a cambios de código): `ruff check .` OK, `mypy app/` OK (52 archivos), `pytest -q` OK (`96 passed`) — coincide con el "Final de fase" reportado al cierre de Fase 10.
- Valores no fijados por el checklist, confirmados explícitamente por el usuario antes de implementar:
  - `highlight.js@11.9.0` vía cdnjs, con temas `github.min.css` (claro) y `github-dark.min.css` (oscuro), alternando según la clase `dark:` ya usada en `chat.html`.
  - Botón de copiar: uno por mensaje completo del asistente + uno adicional por cada bloque de código individual dentro del mensaje.
  - Feedback visual: el botón cambia brevemente a "Copiado ✓" y vuelve al estado original tras un tiempo corto (2000 ms).
  - Resaltado de sintaxis: detección automática de lenguaje siempre (`hljs.highlightElement`), sin depender de que el bloque markdown especifique el lenguaje.
  - Se aplica por igual a mensajes cargados en el historial (`GET /chat`) y a mensajes nuevos insertados por streaming/HTMX.
- Hallazgo no cubierto por el checklist ni por los 5 valores anteriores, bloqueado y confirmado con el usuario antes de escribir código: el proyecto no tiene ningún parser de markdown (ni librería Python ni JS) — `msg.content` se renderiza siempre como texto plano escapado por Jinja (`app/templates/partials/message.html`, antes de esta fase), por lo que no existían bloques `<pre><code>` reales sobre los que `highlight.js` pudiera operar. Se confirmó implementar un parser mínimo propio de fences ```` ``` ```` en JS (sin nueva dependencia de markdown), que opera sobre el texto ya decodificado (vía `dataset.rawContent`) y solo convierte los tramos delimitados por fences en `<pre><code class="language-x">`; el resto del mensaje se mantiene como texto plano con `whitespace-pre-wrap`, igual que antes de esta fase.
- Bugs encontrados/corregidos: ninguno preexistente en el código tocado.
- Discrepancias de spec: sin discrepancias de spec (el único valor no cubierto por el checklist original fue confirmado con el usuario antes de escribir código, ver punto anterior).
- Decisiones de implementación no cubiertas explícitamente por el checklist ni por las preguntas de alcance (aplicadas por consistencia mínima con lo confirmado, documentadas aquí en vez de asumidas en silencio):
  - El contenido original y sin procesar de cada mensaje del asistente se guarda en el atributo `data-raw-content` del contenedor (`app/templates/partials/message.html`), escapado por el autoescape estándar de Jinja; el botón "copiar mensaje" copia ese valor decodificado por el navegador (`el.dataset.rawContent`), preservando las fences ```` ``` ```` originales tal como las escribió el asistente, en vez del texto ya transformado a HTML.
  - El botón "copiar bloque de código" copia `codeEl.textContent` del `<code>` ya resaltado por `highlight.js` (que no altera el texto, solo lo envuelve en `<span>` de color), evitando necesidad de guardar el código dos veces.
  - Además de `GET /chat` (historial) y el streaming SSE (`message_html`), se detectó un tercer punto de inserción de `partials/message.html` en `#messages` vía HTMX puro (cambio de sesión en el sidebar y aprobación/rechazo de confirmación HITL, ambos con `hx-target="#messages"`); se cubrió con un listener global `htmx:afterSwap` que reutiliza la misma función de resaltado/inyección (`enhanceAssistantMessages`), consistente con que los 5 valores confirmados mencionan explícitamente "streaming/HTMX" como un mismo caso.
  - El botón de copiar por mensaje y el resaltado solo se agregan a mensajes con `msg.role == "assistant"` y `msg.content` no vacío; mensajes de error renderizados solo en el cliente (`appendAssistantError`, que no pasa por `partials/message.html`) no son mensajes reales del asistente y quedan fuera, sin botón ni resaltado.
  - `enhanceAssistantMessage()` usa un guard de idempotencia (`dataset.hlProcessed`) para no reprocesar un mismo mensaje dos veces cuando se llama sobre el documento completo repetidas veces (ej. tras cada swap de HTMX).
- Fuera de alcance de esta fase, no tocado por instrucción explícita del usuario: el bug preexistente de `chat.html` (`renderOutgoingMessage` limpia `#chat-input` antes de construir `FormData`, ya señalado en la Fase 9) y la discrepancia `docs/ui-design.md` (`/api/chat` vs. `/api/chat/stream`); ambos quedan asignados a Fase 14.
- Revisión manual documentada (criterio de aceptación de esta fase; sin test automatizado razonable, mismo enfoque que Fase 9):
  - Render directo de `partials/message.html` vía `Jinja2Templates.get_template(...).render(...)` con un mensaje de usuario con caracteres especiales (`<script>`, comillas, `&`) y un mensaje de asistente con un bloque de código Python embebido: se verificó que el escapado en `data-raw-content` y en el texto es correcto (entidades HTML válidas dentro de un atributo entre comillas dobles) y que la estructura del `<div data-assistant-content>` es válida (a diferencia de un `<p>`, admite hijos de bloque como `<pre>` sin que el parser HTML lo cierre implícitamente).
  - Verificación de sintaxis del bloque `<script>` completo de `chat.html` con `node --check` (OK).
  - Simulación en Node del parser de fences (`renderAssistantContentHtml`) extraído del script real de `chat.html`, con texto que incluye caracteres a escapar (`<`, `"`, `&`) dentro y fuera del bloque de código: confirma que el bloque de código anotado (```` ```python ````) se envuelve en `<pre><code class="language-python">` con el código correctamente escapado, y que el texto fuera del bloque también se escapa sin doble-escapado (porque opera sobre el texto ya decodificado desde el atributo, no sobre HTML ya escapado).
  - Se corrió la suite existente de tests que hacen `GET /chat` (`tests/integration/test_chat_hitl.py`, `tests/e2e/test_web_chat_flow.py`, entre otros) para confirmar que el HTML de `chat.html`/`message.html` sigue renderizando sin error de plantilla con los cambios aplicados.
  - No se probó en navegador real contra los servicios de producción configurados en `.env` (Supabase/OpenRouter), por instrucción explícita del usuario.
- Resultado de validaciones:
  - Final de fase: `ruff check .` OK, `mypy app/` OK (52 archivos), `pytest -q` OK (`96 passed`, sin cambios respecto del baseline — no se agregaron tests nuevos, consistente con el criterio de aceptación de esta fase).
- Fase NO marcada como HECHO por instrucción explícita del usuario; queda en estado `EN PROGRESO` en `docs/agent_total-plan.md` con el checklist tildado.
- Verificación técnica de autoescape previa al cierre: `grep -n "Jinja2Templates\|autoescape" app/main.py app/pages/*.py app/routers/*.py` no encontró ninguna configuración propia del proyecto que desactive autoescape (solo instanciaciones de `Jinja2Templates(directory="app/templates")` en `app/main.py`, `app/pages/chat.py`, `app/routers/auth.py`, `app/pages/onboarding.py`, `app/pages/settings.py`, `app/routers/chat.py`, `app/routers/sessions.py`); se confirmó en el código fuente de Starlette (`starlette/templating.py`) que `Jinja2Templates` construye el `jinja2.Environment` con `autoescape=jinja2.select_autoescape()`, que por defecto activa autoescape para archivos `.html` — consistente con lo asumido en la revisión manual de esta fase (escapado de `data-raw-content` y del contenido de mensajes).
- Confirmación explícita del usuario en el chat de planificación (no solo durante la sesión de implementación) sobre el parser propio de fences y el alcance limitado a bloques de código (sin renderizado de markdown general); fase cierra sin discrepancias pendientes.

## Fase 12 - Punto de extensión MCP (intento, sin cerrar como HECHO)

- Fecha: 2026-07-05.
- Baseline de fase (previo a cambios de código): `ruff check .` OK, `mypy app/` OK (52 archivos), `pytest -q` OK (`96 passed`) — coincide con el "Final de fase" reportado al cierre de Fase 11, sobre working tree limpio en el commit `3c904bc`.
- Hallazgo previo a implementar, verificado antes de preguntar: no existe ningún SDK MCP instalado ni declarado (`mcp`, `langchain-mcp-adapters` ausentes de `pyproject.toml` y del entorno virtual); `app/agent/graph.py` ya es genérico respecto de tools (`tool_executor_node` solo consulta `TOOL_HANDLERS` de `app/tools/adapters.py` y `get_tool_risk`/`tool_requires_confirmation` de `app/tools/catalog.py`, sin ninguna rama por nombre de tool).
- Valores no fijados por el checklist, confirmados explícitamente por el usuario antes de implementar:
  - Tool de ejemplo: completamente ficticia/stub, sin conexión a ningún servidor MCP real y sin agregar dependencia nueva (`mcp`/`langchain-mcp-adapters`).
  - Documentación del ejemplo de referencia: archivo nuevo dedicado `docs/mcp-extension-example.md` (no se amplía `docs/technical-brief.md` §10.4 en esta fase).
  - Se agrega una variable de entorno ilustrativa (`MCP_EXAMPLE_SERVER_URL`) a `.env.example`, siguiendo el patrón de `EVAL_USER_ID`, para mostrar el patrón de configuración que tendría una integración MCP real futura, aunque el stub no se conecta a ella de verdad.
  - Alcance de "sin tocar `graph.py`": se permitía tocar `graph.py` si fuera algo genérico no específico de MCP; no fue necesario ningún cambio, `graph.py` queda con diff cero.
- Bugs encontrados/corregidos: ninguno preexistente en el código tocado.
- Discrepancias de spec: sin discrepancias de spec (el único valor no cubierto por el checklist original -- qué tool de ejemplo usar -- fue confirmado con el usuario antes de escribir código).
- Archivos nuevos: `app/tools/mcp/__init__.py`, `app/tools/mcp/example_tool.py` (`MCP_EXAMPLE_TOOL_ID = "mcp_example_ping"`, handler `handle_mcp_example_ping` que simula la respuesta de una tool MCP real y lee `MCP_EXAMPLE_SERVER_URL` solo para incluirla en la respuesta simulada, sin conectarse a ella), `docs/mcp-extension-example.md`, `tests/unit/test_mcp_extension.py`.
- Archivos tocados: `app/tools/catalog.py` (nueva `ToolDefinition` `mcp_example_ping`, `risk="low"`), `app/tools/adapters.py` (import y registro en `TOOL_HANDLERS`), `app/config.py` (campo opcional `mcp_example_server_url`), `.env.example` (`MCP_EXAMPLE_SERVER_URL=`).
- Demostración de registro sin tocar `graph.py` (criterio de aceptación): `tests/unit/test_mcp_extension.py::test_mcp_example_tool_executes_via_generic_tool_executor_node` invoca `tool_executor_node` importado sin cambios desde `app.agent.graph` con un `AIMessage.tool_calls` que referencia `mcp_example_ping`, y verifica que se ejecuta por la misma ruta genérica (`run_with_tracking`, monkeypatcheado igual que en `tests/unit/test_runtime_tracking.py` para `get_user_preferences`) que cualquier otra tool `low` ya existente, sin ninguna rama de código dedicada a MCP en el runtime.
- Revisión manual documentada (parte del criterio de aceptación; complementaria al test automatizado):
  - `git diff --stat -- app/agent/graph.py` confirmado sin salida (cero líneas de diff).
  - `docs/mcp-extension-example.md` describe el mecanismo, los archivos tocados y los pasos concretos para reemplazar el stub por un cliente MCP real.
- Resultado de validaciones:
  - Final de fase: `ruff check .` OK, `mypy app/` OK (54 archivos), `pytest -q` OK (`99 passed`, +3 respecto del baseline por `tests/unit/test_mcp_extension.py`).
  - Tests de aceptación: `tests/unit/test_mcp_extension.py` (`test_mcp_example_tool_registered_in_catalog`, `test_mcp_example_handler_returns_stub_response`, `test_mcp_example_tool_executes_via_generic_tool_executor_node`).
- Fase NO marcada como HECHO por instrucción explícita del usuario; queda en estado `EN PROGRESO` en `docs/agent_total-plan.md` con el checklist tildado. Sin commitear por instrucción explícita del usuario (cierre pendiente de confirmación separada, para no repetir el problema de la sesión anterior de un cierre de fase mezclado sin confirmar).
- Confirmación explícita del usuario en el chat de planificación (no solo durante la sesión de implementación) sobre las 4 respuestas de alcance; fase cierra sin discrepancias pendientes.

## Fase 13 - Sesiones: título automático, archivar y eliminar (intento, sin cerrar como HECHO)

- Fecha: 2026-07-05.
- Baseline de fase (previo a cambios de código): `ruff check .` OK, `mypy app/` OK (54 archivos), `pytest -q` OK (`99 passed`) — coincide con el "Final de fase" reportado al cierre de Fase 12, sobre working tree limpio en el commit `6a17af6`.
- Investigación previa a preguntar (punto 1 del checklist de preguntas): se verificó `pip show langgraph-checkpoint-postgres` (versión `3.1.0` instalada) y se inspeccionó el código fuente instalado de `AsyncPostgresSaver` (`langgraph/checkpoint/postgres/aio.py:340-361`): el método `adelete_thread(thread_id: str) -> None` **sí existe** en la versión instalada y ya hace `DELETE FROM checkpoints/checkpoint_blobs/checkpoint_writes WHERE thread_id = %s`. No fue necesario inspeccionar el schema real ni escribir `DELETE` manual; se usa `adelete_thread` directamente sobre la instancia que devuelve `get_checkpointer()`.
- Valores no fijados por el checklist, confirmados explícitamente por el usuario antes de implementar:
  - Texto exacto de `hx-confirm` para "Eliminar": `"¿Eliminar esta conversación? Esta acción no se puede deshacer."`.
  - Límite de reintentos de generación de título: sin límite; se reintenta en cada turno mientras `title IS NULL` (sin columna nueva de conteo de intentos, consistente con que la migración 00007 solo agrega `title`).
  - Orden de operaciones en el hard-delete: limpieza best-effort del checkpointer **primero**, `DELETE FROM agent_sessions` **después** (razón: maximiza que el contenido de chat quede efectivamente inaccesible tras el borrado; si el checkpointer fallara y el orden fuera inverso, quedaría contenido recuperable vía checkpointer con la sesión ya "invisible" en la UI, que es exactamente el riesgo que este checklist busca evitar).
  - Definición de "primer mensaje de usuario de la sesión" quando el primero es solo-adjuntos: se usa el primer `HumanMessage` con `content` no vacío (se ignoran mensajes solo-adjuntos al elegir la semilla); si ningún mensaje de usuario tiene texto todavía, no se genera título en ese turno (`title` sigue `NULL`, se reintenta en turnos siguientes con el mismo mecanismo).
- Migración `migrations/00007_sessions_title_and_archive.sql` creada y revisada (columna `title` aditiva/nullable + `DROP CONSTRAINT IF EXISTS agent_sessions_status_check` / `ADD CONSTRAINT` ampliando a `('active','archived','closed')`, mismo patrón que `migrations/00003`).
- Verificación previa a la aplicación (lectura sobre el Supabase real vía `DATABASE_URL`/`asyncpg`, mismo mecanismo que `scripts/check_connections.py`): `agent_sessions` no tenía columna `title` (9 columnas: `id`, `user_id`, `channel`, `status`, `budget_tokens_used`, `budget_tokens_limit`, `created_at`, `updated_at`, `last_used_at`); el constraint real se llamaba `agent_sessions_status_check` con definición `CHECK ((status = ANY (ARRAY['active'::text, 'closed'::text])))`; la tabla tenía 0 filas (sin riesgo de valores de `status` fuera de rango).
- Aplicación autorizada explícitamente por el usuario en el chat de planificación, tras revisar esa verificación previa: migración aplicada contra Supabase real (conexión directa vía `DATABASE_URL`/`asyncpg`, mismo mecanismo usado en la extensión autorizada de Fase 2 para aplicar `00001`-`00006`), dentro de una única transacción.
- Verificación posterior a la aplicación (misma consulta de solo lectura, repetida): `agent_sessions.title` ahora existe (`data_type: text`, `is_nullable: YES`, `column_default: None`); `agent_sessions_status_check` ahora tiene definición `CHECK ((status = ANY (ARRAY['active'::text, 'archived'::text, 'closed'::text])))`; la tabla sigue con 0 filas. Migración `00007` **aplicada y verificada** contra Supabase real.
- Hallazgo fuera de alcance de esta fase, para revisión futura (Fase 14 o posterior, no un bug de Fase 13): el esquema real de `agent_sessions` tiene 4 columnas (`budget_tokens_used`, `budget_tokens_limit`, `created_at`, `updated_at`) que no están reflejadas en el modelo Pydantic `AgentSession` de `app/db/queries/sessions.py` (que solo expone `id`, `user_id`, `channel`, `status`, `last_used_at`, y ahora `title`). Preexistente a esta fase, no tocado; no afecta la seguridad de la migración 00007 ni el funcionamiento de esta fase, pero queda registrado como deuda de sincronización schema-modelo a revisar en una sesión dedicada futura.
- Bugs encontrados/corregidos: ninguno preexistente en el código tocado. Efecto colateral detectado y corregido durante la propia implementación (no un bug preexistente, sino una consecuencia directa de agregar `session.title` en el trigger de `app/routers/chat.py`): tres tests de integración (`tests/integration/test_chat_attachments.py`, `tests/integration/test_chat_model_selection.py`, `tests/integration/test_chat_request_contract.py`) mockeaban la sesión como `SimpleNamespace(id="session-1", user_id="user-1")` sin atributo `title`, lo que rompía con `AttributeError` al evaluar `session.title is None`; se corrigió agregando `title=None` a esos mocks.
- Discrepancias de spec: sin discrepancias de spec (los 4 valores no fijados por el checklist fueron confirmados con el usuario antes de escribir código; el punto de investigación del checkpointer se resolvió con evidencia directa del código instalado, sin necesitar pregunta).
- Decisiones de implementación no cubiertas explícitamente por el checklist ni por las preguntas de alcance (aplicadas por consistencia mínima con lo ya confirmado, documentadas aquí en vez de asumidas en silencio):
  - Mecanismo para que el backend sepa cuál es la "sesión actual" en las rutas `archive`/`delete`: no existe cookie ni tracking server-side de "sesión mostrada actualmente" (el `current_session_id` de `GET /chat` se resuelve por `last_used_at` descendente, no por estado de sesión HTTP); se optó por pasar `current_session_id` como campo adicional vía `hx-vals` en los botones del menú de 3 puntos (mismo patrón ya usado en `partials/confirmation.html` para `tool_call_id`/`action`), recibido como `Form(default="")` en ambas rutas nuevas.
  - Respuesta "partial vacío para remover item": implementado como `HTMLResponse(content="", status_code=200)` con `hx-target="closest [data-session-item]"` y `hx-swap="outerHTML"` en los botones "Archivar"/"Eliminar" de `session_item.html`, de forma que el propio contenedor de la sesión (incluyendo su menú) se reemplaza por una respuesta vacía y desaparece del sidebar.
  - Truncado defensivo a 6 palabras y remoción de comillas/punto final: además de pedírselo al modelo en el prompt, `_clean_title()` en `app/agent/session_title.py` aplica el recorte y la limpieza de forma programática como red de seguridad ante un modelo que no respete la instrucción exactamente.
- Archivos nuevos: `migrations/00007_sessions_title_and_archive.sql`, `app/agent/session_title.py`, `tests/unit/test_sessions_queries.py`, `tests/unit/test_session_title.py`, `tests/integration/test_sessions_routes.py`, `tests/integration/test_session_item_rendering.py`.
- Archivos tocados: `app/db/queries/sessions.py` (`AgentSession.title`, `.limit(10)` en `list_sessions()`, `update_session_title()`, `archive_session()`, `delete_session()`), `app/routers/chat.py` (trigger de generación de título junto a `flush_session_memory` en `/api/chat` y `/api/chat/stream`), `app/routers/sessions.py` (rutas `POST /{id}/archive` y `POST /{id}/delete`, limpieza best-effort del checkpointer), `app/templates/partials/session_item.html` (fallback de título, menú de 3 puntos, botones archivar/eliminar), `app/templates/chat.html` (`toggleSessionMenu(id)`), y los 3 tests de integración mencionados arriba (fix de mocks).
- Resultado de validaciones:
  - Final de fase: `ruff check .` OK, `mypy app/` OK (55 archivos), `pytest -q` OK (`115 passed`, +16 respecto del baseline).
  - Tests de aceptación: `tests/unit/test_sessions_queries.py::test_list_sessions_orders_desc_and_limits_to_10` (límite 10 + orden descendente); `tests/integration/test_session_item_rendering.py` (fallback a fecha cuando `title` es `NULL`, fallback a "Nueva sesión" cuando tampoco hay `last_used_at`, título mostrado cuando existe, `hx-confirm` solo en "Eliminar"); `tests/integration/test_sessions_routes.py` (404/403 por ownership, archivar/eliminar sesión actual con `HX-Redirect: /chat` y creación de sesión nueva, archivar/eliminar sesión no actual con partial vacío sin redirect, orden checkpointer-luego-agent_sessions verificado explícitamente, tolerancia a fallo del checkpointer sin bloquear el borrado); `tests/unit/test_session_title.py` (usa primer mensaje con texto ignorando solo-adjuntos, trunca a 6 palabras, no genera título si ningún mensaje tiene texto, nunca lanza excepción ante fallo).
- Fase NO marcada como HECHO por instrucción explícita del usuario; queda en estado `EN PROGRESO` en `docs/agent_total-plan.md` con el checklist tildado. Migración `00007` aplicada y verificada contra Supabase real. Sin commitear por instrucción explícita del usuario (commit pendiente como paso separado, tras confirmar la migración aplicada).
- Confirmación explícita del usuario en el chat de planificación (no solo durante la sesión de implementación) sobre las 4 respuestas de alcance y sobre la aplicación de la migración 00007 contra Supabase real tras verificación previa/posterior; fase cierra sin discrepancias pendientes.
