# Cómo retomar agent_total en una sesión nueva

Este proyecto está diseñado para sobrevivir pérdida de contexto conversacional.
Todo lo esencial vive en archivos del repo, no en memoria de chat.

## Retomar en Cursor (sesión nueva, sin historial previo)
1. Los archivos .cursor/.rules/*.mdc se cargan automáticamente
   (alwaysApply: true); no hace falta reexplicar reglas ni candado.
2. Leer docs/agent_total-plan.md para saber qué fase está HECHO y cuál sigue.
3. Leer docs/agent_total-changelog.md para el porqué de decisiones y
   desviaciones ya resueltas (no reabrir lo ya decidido ahí).
4. Ejecutar solo la fase que el usuario autorice explícitamente en el
   prompt de esa sesión. Nunca avanzar de fase sin autorización nueva.

## Retomar con un asesor LLM (ej. Claude) en una conversación nueva
1. Antes de pedir el prompt de la siguiente fase, pegar/subir el contenido
   actual de docs/agent_total-plan.md y docs/agent_total-changelog.md.
2. El asesor debe generar cada prompt de autorización de fase de forma
   autocontenida: citando archivo y sección exactos, sin depender de
   "como dijimos antes" ni de memoria conversacional.
3. Ante cualquier ambigüedad, el asesor debe preguntar en vez de asumir,
   igual que en el resto de este proceso.
