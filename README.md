# agent_total

Plantilla de agente conversacional genérico y extensible sobre FastAPI + LangGraph + Supabase + OpenRouter + Langfuse, con UI SSR en Jinja2/HTMX.

## Qué es esto

`agent_total` es una base para construir agentes de chat con memoria de largo plazo, HITL (human-in-the-loop) para acciones riesgosas, y un punto de extensión de herramientas pensado para no tener que tocar el runtime del grafo cada vez que se agrega una integración nueva.

No resuelve un dominio específico: el objetivo es que cualquier desarrollo futuro — por ejemplo, conectar un servidor MCP a una base de datos externa para que el chat responda preguntas en lenguaje natural contra esa base — se agregue por catálogo + adapter, reusando el runtime, el checkpointing, la memoria y la trazabilidad ya construidos.

## Arquitectura en 4 líneas

- **Runtime**: LangGraph con grafo `memory_injection -> compaction -> agent -> tools`, checkpointing en Postgres (`AsyncPostgresSaver`), HITL genérico vía `interrupt()`/`Command(resume=...)`.
- **Tools**: catálogo + política de riesgo (`app/tools/catalog.py`) + handlers (`app/tools/adapters.py`); agregar una tool nueva no requiere tocar `app/agent/graph.py`.
- **Memoria**: extracción y clasificación automática (`episodic`/`semantic`/`procedural`), inyección real en el prompt antes de cada turno, filtro de privacidad antes de persistir.
- **UI**: SSR + HTMX (Jinja2), sin SPA; `POST /api/chat/stream` (SSE) es la ruta real que usa la UI de chat.

Todo lo esencial de esta plantilla vive en archivos del repo (código + docs), no en memoria conversacional de ninguna sesión de asistente.

## Documentación

| Documento | Qué describe |
| --- | --- |
| `docs/technical-brief.md` | Brief de producto: qué es `agent_total` y qué debe hacer |
| `docs/ui-design.md` | Qué se espera de la UI (contrato visual y HTMX) |
| `docs/implementation-summary.md` | Cómo está construido en la práctica (mecanismos internos) |
| `docs/extending.md` | El plan que se ejecutó para implementar el brief, y cómo aplicarlo a extensiones nuevas |
| `docs/mcp-extension-example.md` | Stub de referencia del punto de extensión MCP |
| `migrations/*.sql` | Modelo de datos, fuente de verdad del esquema |
| `.cursor/.rules/*.mdc` | Reglas de arquitectura, seguridad, testing y colaboración |

`agent_total` es un producto completo y funcional; no hay trabajo pendiente en su alcance
actual. Las decisiones de diseño sobre qué queda deliberadamente fuera de alcance están en
`docs/implementation-summary.md`.
