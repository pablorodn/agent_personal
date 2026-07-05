# Resumen as-built - agent_total

> Producido al cierre de la Fase 15 (`docs/agent_total-plan.md`), la sesión de consolidación
> final de la plantilla. Este documento resume qué se construyó realmente, qué quedó
> deliberadamente fuera de alcance, y deja una lección aprendida concreta para quien
> reutilice este repo. El detalle completo de cada decisión, bug y discrepancia vive en
> `docs/agent_total-changelog.md`.

## Qué se construyó

`agent_total` es un agente conversacional sobre FastAPI + LangGraph + Supabase + OpenRouter,
con UI SSR en Jinja2/HTMX, pensado como plantilla reutilizable más que como producto de
dominio específico. El runtime terminado incluye:

- Memoria de largo plazo real: inyección efectiva de recuerdos relevantes en el prompt antes
  de cada turno, con filtro de privacidad aplicado antes de persistir.
- Compactación de contexto en dos etapas (resumen LLM estructurado por secciones + truncado
  duro de respaldo) con circuit breaker ante fallos consecutivos de la etapa LLM.
- Mecanismo HITL genérico (`interrupt()` / `Command(resume=...)`) para tools de riesgo
  `medium`/`high`, con tracking de ejecución para todas las tools (incluidas las de riesgo
  `low`) y un límite duro de iteraciones de tools por turno.
- Langfuse conectado al `invoke` real del grafo (no solo un helper sin cablear).
- Evaluaciones que corren contra el runtime real (`run_agent()`), no contra un stub.
- Adjuntos multimodales en chat (imágenes y PDF) con validación de tipo/tamaño/cantidad e
  indicador de historial.
- Selector de modelo en chat y en settings, validado server-side contra una lista curada y
  persistido automáticamente en `profiles.default_model`.
- Punto de extensión MCP demostrado end-to-end: una tool nueva se registra íntegramente vía
  catálogo + adapter, sin tocar `app/agent/graph.py`.
- Gestión completa de sesiones: título automático generado por LLM a partir del primer
  mensaje de usuario, archivado, y hard-delete real que además limpia el estado del
  checkpointer de LangGraph asociado (sin dejar historial recuperable).
- Hardening final de cierre: arranque migrado a `lifespan`, cookies de sesión con
  `secure`/`https_only` condicional por entorno (`ENVIRONMENT`), y documentación del
  contrato real de `POST /api/chat/stream`.

## Qué quedó fuera de alcance a propósito

- Pantalla de archivados y recuperación de sesiones archivadas: archivar solo oculta la
  sesión del sidebar (`status='archived'`); no hay UI para verlas ni restaurarlas.
- Click-outside-to-close en el menú de 3 puntos de cada sesión: el menú se cierra solo al
  abrir otro menú, no al hacer click fuera. Limitación aceptada explícitamente en Fase 13.
- Integración MCP real: el punto de extensión (Fase 12) es un scaffolding stub que demuestra
  el mecanismo de registro; no se conecta a ningún servidor MCP real ni agrega un cliente/SDK
  MCP como dependencia.
- Renderizado de markdown general en mensajes del asistente: solo los bloques de código
  delimitados por fences ` ``` ` se resaltan con `highlight.js` (Fase 11); el resto del texto
  permanece plano (sin negritas, listas, links, etc.), por decisión explícita para no
  incorporar una librería de markdown nueva.
- Comportamiento ideal de `microcompact` (etapa 1 de compactación): hoy es un truncado duro
  por slice que descarta mensajes antiguos; la idea de reemplazarlos por marcadores
  compactos en vez de descartarlos queda documentada como pendiente en
  `docs/technical-brief.md` §7, sin implementar.

## Lección aprendida: el bug crítico de `chat.html`

Ningún flujo de UI se probó en navegador real durante el desarrollo por fases (para evitar
costo/riesgo contra servicios de producción). Esto permitió que un bug crítico de orden de
ejecución en `chat.html` — `renderOutgoingMessage()` vaciaba `#chat-input` antes de construir
`new FormData(form)`, lo que hacía llegar el campo `message` vacío al backend en todo envío
de texto normal — pasara desapercibido durante 13 fases. Se detectó y corrigió recién en
Fase 14, verificado empíricamente con un test de jsdom (`tests/js/test_submit_chat_formdata.mjs`)
que reprodujo el bug real (revirtiendo temporalmente el orden y confirmando que el campo
llegaba vacío) antes de confirmar que el fix lo resolvía. Quien extienda esta plantilla
debería considerar agregar al menos un smoke test de navegador real (Playwright/Cypress)
antes de producción.

## Dónde está el registro completo

`docs/agent_total-changelog.md` contiene, fase por fase, cada bug encontrado y corregido,
cada discrepancia entre spec y código, cada sesión dedicada de documentación, y el resultado
de `ruff check .` / `mypy app/` / `pytest -q` al cierre de cada fase. Este resumen no
reemplaza ese registro: es la vista consolidada para no tener que reconstruirlo leyendo las
15 fases una por una.
