# agent_total

Plantilla de agente genérico y extensible sobre FastAPI + LangGraph + Supabase + OpenRouter + Langfuse, con UI SSR en Jinja2/HTMX.

## Objetivo

`agent_total` prioriza un runtime sólido y reusable: grafo estable, políticas de riesgo, checkpointing, memoria, trazabilidad y una vía clara para extender herramientas sin reescribir el núcleo.

## Estado actual del repositorio

- Existe implementación funcional de autenticación, onboarding de 4 pasos, chat web multi-sesión con sidebar y settings.
- El runtime base de LangGraph está conectado como `memory_injection -> compaction -> agent -> tools`.
- El mecanismo HITL con `interrupt()` y `Command(resume=...)` está presente y sigue siendo genérico para tools de riesgo `medium/high`.
- Hay file tools con flag `FILE_TOOLS_ENABLED` y confinamiento de path.
- Memoria de largo plazo, compactación de dos etapas con circuit breaker, Langfuse conectado al `invoke` real, y evaluaciones contra el runtime real están implementados y en `HECHO` (Fases 4-8).
- Adjuntos multimodales, selector de modelo, punto de extensión MCP, gestión completa de sesiones (título automático, archivar, hard-delete con limpieza de checkpointer) y el hardening final de cierre también están en `HECHO` (Fases 9-14).
- Las 15 fases del plan están cerradas. Ver `docs/agent_total-as-built.md` para el resumen consolidado de qué se construyó, qué quedó fuera de alcance a propósito, y la lección aprendida principal del proyecto.

## Fuentes de verdad

| Tema | Fuente principal | Documentos asociados |
| --- | --- | --- |
| Arquitectura y runtime | `docs/technical-brief.md` | `.cursor/.rules/architecture.mdc`, `.cursor/.rules/guardrails.mdc` |
| UI y comportamiento HTMX | `docs/ui-design.md` | Tabla de rutas de `docs/technical-brief.md` |
| Modelo de datos | `migrations/*.sql` | Sección de datos en `docs/technical-brief.md` |
| Seguridad y testing | `.cursor/.rules/*.mdc` | `docs/technical-brief.md`, `docs/ui-design.md` |
| Plan de implementación por fases | `docs/agent_total-plan.md` | Estado operativo del proyecto |
| Resumen as-built y lecciones aprendidas | `docs/agent_total-as-built.md` | `docs/agent_total-changelog.md` |

## Pendientes reales de esta etapa

- Ninguno bloqueante: las 15 fases del plan (`docs/agent_total-plan.md`) están en `HECHO`.
- Fuera de alcance a propósito (no pendiente, decisión consciente): pantalla de archivados/recuperación de sesiones, click-outside-to-close del menú de sesión, integración MCP real (solo scaffolding stub), renderizado de markdown general en mensajes (solo bloques de código), comportamiento ideal de `microcompact` con marcadores en vez de truncado duro. Detalle completo en `docs/agent_total-as-built.md`.

