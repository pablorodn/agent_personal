# agent_total

Plantilla de agente genérico y extensible sobre FastAPI + LangGraph + Supabase + OpenRouter + Langfuse, con UI SSR en Jinja2/HTMX.

## Objetivo

`agent_total` prioriza un runtime sólido y reusable: grafo estable, políticas de riesgo, checkpointing, memoria, trazabilidad y una vía clara para extender herramientas sin reescribir el núcleo.

## Estado actual del repositorio

- Existe implementación funcional de autenticación, onboarding de 4 pasos, chat web multi-sesión con sidebar y settings.
- El runtime base de LangGraph está conectado como `memory_injection -> compaction -> agent -> tools`.
- El mecanismo HITL con `interrupt()` y `Command(resume=...)` está presente y sigue siendo genérico para tools de riesgo `medium/high`.
- Hay file tools con flag `FILE_TOOLS_ENABLED` y confinamiento de path.
- La compactación LLM, la inyección real de memoria, el wiring real de Langfuse y las evaluaciones reales aún están pendientes de completar.

## Fuentes de verdad

| Tema | Fuente principal | Documentos asociados |
| --- | --- | --- |
| Arquitectura y runtime | `docs/technical-brief.md` | `.cursor/.rules/architecture.mdc`, `.cursor/.rules/guardrails.mdc` |
| UI y comportamiento HTMX | `docs/ui-design.md` | Tabla de rutas de `docs/technical-brief.md` |
| Modelo de datos | `migrations/*.sql` | Sección de datos en `docs/technical-brief.md` |
| Seguridad y testing | `.cursor/.rules/*.mdc` | `docs/technical-brief.md`, `docs/ui-design.md` |
| Plan de implementación por fases | `docs/agent_total-plan.md` | Estado operativo del proyecto |

## Pendientes reales de esta etapa

- Activar memoria de largo plazo end-to-end (inyección efectiva y filtro de privacidad previo a persistencia).
- Completar compactación de dos etapas con circuit breaker (hoy solo está la etapa 1).
- Conectar Langfuse en el `invoke` real del grafo y reemplazar evaluaciones stub por evaluaciones contra runtime real.
- Incorporar adjuntos multimodales en chat y selector de modelo con persistencia en `profiles.default_model`.
- Reducir y estabilizar el catálogo de tools al set mínimo definido para `agent_total` y preparar el punto de extensión MCP.

