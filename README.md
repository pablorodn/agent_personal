# Agente Personal MVP

Repositorio en fase de brief para construir un agente personal conversacional con FastAPI, LangGraph, Supabase, Jinja2/HTMX y Telegram.

## Estado actual

Este repositorio contiene la implementación del agente personal: estructura `app/` completa (routers, páginas, runtime LangGraph, tools, servicios, DB y templates), `pyproject.toml`, `.env.example`, `evals/`, suite de tests y las migraciones de Supabase.

Pendientes de conexión conocidos (ver `docs/ui-design.md` §12): `app/pages/index.py`, `app/pages/chat.py` y `app/pages/settings.py` aún usan datos de marcador en algunos puntos y deben leer/escribir Supabase real; la topbar de navegación (`partials/topbar.html`) debe montarse en `chat.html` y `settings.html`.

## Orden recomendado de lectura

1. `docs/technical-brief.md` — documento rector de arquitectura, runtime, datos, seguridad e integraciones.
2. `docs/ui-design.md` — contrato visual y comportamiento HTMX de la interfaz web.
3. `.cursor/.rules/*.mdc` — reglas operativas para mantener consistencia durante la implementación.
4. `migrations/*.sql` — fuente de verdad del esquema Supabase.

## Fuentes de verdad


| Tema                              | Fuente principal          | Documentos asociados que deben mantenerse alineados                              |
| --------------------------------- | ------------------------- | -------------------------------------------------------------------------------- |
| Arquitectura y runtime            | `docs/technical-brief.md` | `.cursor/.rules/architecture.mdc`, `.cursor/.rules/guardrails.mdc`               |
| UI y HTMX                         | `docs/ui-design.md`       | Tabla de rutas en `docs/technical-brief.md`                                      |
| Modelo de datos                   | `migrations/*.sql`        | Sección 13 de `docs/technical-brief.md`                                          |
| Seguridad, HITL y riesgo de tools | `docs/technical-brief.md` | `.cursor/.rules/security.mdc`, `.cursor/.rules/testing.mdc`, `docs/ui-design.md` |
| Variables de entorno              | `docs/technical-brief.md` | futuro `.env.example`                                                            |


## Principios clave

- Un único runtime de agente para web, Telegram y cron.
- Supabase/Postgres como fuente de verdad para sesiones, mensajes, tools, integraciones, tareas y memoria.
- Acciones sensibles siempre controladas por política de riesgo y confirmación humana cuando corresponda.
- Frontend server-rendered con Jinja2 + HTMX; evitar introducir SPA en el MVP.
- Cambios de esquema solo mediante migraciones incrementales.

## Pendientes

- Conectar `app/pages/` a datos reales de Supabase (index, chat, settings) — ver `docs/ui-design.md` §12.
- Montar `partials/topbar.html` en `chat.html` y `settings.html` con `agent_name` y `active_nav`.
- Mantener verde la suite: `ruff check .`, `mypy app/`, `pytest`.

