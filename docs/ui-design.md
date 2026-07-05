# UI Design - agent_total (Jinja2 + HTMX)

> Contrato visual y de comportamiento para la UI SSR/HTMX de `agent_total`.
> Este documento refleja alcance real actual + objetivos de la etapa.

## 1) Principios de UI

- Mantener SSR + HTMX, sin SPA.
- Las respuestas de interacción deben ser partials HTML o `HX-Redirect`.
- La UI no ejecuta políticas de seguridad; solo invoca endpoints del backend.
- Estado de sesión y del flujo HITL siempre proviene de servidor.

## 2) Pantallas principales en alcance

- `GET /login`
- `GET /signup`
- `GET /onboarding` (wizard 4 pasos)
- `GET /chat` (multi-sesión con sidebar)
- `GET /settings`

## 3) Topbar y navegación

Estado real actual:

- La topbar existe y está montada en pantallas autenticadas.
- `chat` y `settings` navegan por links normales (`<a href>`).
- `logout` usa `hx-post` y `HX-Redirect`.

No se considera pendiente en esta etapa.

## 4) Chat web: estado actual y objetivo

### Estado actual

- Chat multi-sesión con sidebar disponible.
- Flujo HTMX de envío y render de respuestas operativo.
- Flujo de confirmación HITL en UI operativo.

### Objetivos de esta etapa

1. Adjuntos multimodales en el formulario del chat.
2. Selector de modelo por usuario.
3. Botón copiar por mensaje del asistente.
4. Resaltado de sintaxis en bloques de código.

### Sidebar de sesiones (objetivo adicional)

- La lista de sesiones se muestra de más reciente a más antigua (`last_used_at desc`) con máximo 10 items.
- Cada item de `partials/session_item.html` muestra `session.title` si existe; fallback a `format_session_date` cuando `title` es `null`.
- Cada item incluye menú de 3 puntos con acciones:
  - `Archivar` (sin confirmación).
  - `Eliminar` (con `hx-confirm`: "¿Eliminar esta conversación? No se puede deshacer.").
- Interacción del menú: JS mínimo inline en `chat.html`, sin librerías ni build step, siguiendo el patrón de `toggleSidebar()`/`scrollToBottom()`.
  - Botón de 3 puntos: `onclick="toggleSessionMenu('{{ session.id }}')"`.
  - Función `toggleSessionMenu(sessionId)`: alterna clase `hidden` sobre `id="session-menu-{{ session.id }}"`.
- Limitación aceptada en esta fase: no se implementa cierre por click afuera (click-outside-to-close); queda como mejora futura.
- En esta etapa no existe pantalla de archivados/papelera.

## 5) HTMX en chat (contrato)

| Acción | Método + ruta | `hx-target` | `hx-swap` | Respuesta |
| --- | --- | --- | --- | --- |
| Enviar mensaje | `POST /api/chat` | `#messages` | `beforeend` | Partial de mensaje o confirmación |
| Confirmar HITL | `POST /api/chat/confirm` | `#messages` | `beforeend` | Partial de mensaje final |
| Crear sesión | `POST /api/sessions` | `#session-list` | `afterbegin` | Partial de sesión |
| Cambiar sesión | `GET /chat/session/{id}` | `#messages` | `innerHTML` | Lista de mensajes |
| Limpiar sesión | `POST /api/sessions/{id}/clear` | `#messages` | `innerHTML` | Vacío |
| Archivar sesión | `POST /api/sessions/{id}/archive` + `hx-vals` con `current_session_id` | `#session-item-{id}` | `outerHTML` | `HX-Redirect: /chat` si era la sesión actual; si no, partial vacío que remueve item |
| Eliminar sesión | `POST /api/sessions/{id}/delete` + `hx-vals` con `current_session_id` + `hx-confirm` | `#session-item-{id}` | `outerHTML` | `HX-Redirect: /chat` si era la sesión actual; si no, partial vacío que remueve item |

## 6) Adjuntos multimodales (objetivo de UI + HTMX)

Contrato objetivo de formulario:

- `input type="file"` con `accept="image/png,image/jpeg,image/webp,application/pdf"`.
- `enctype="multipart/form-data"` en `#chat-form`.
- Envío de texto + archivos en una sola request `POST /api/chat`.
- Debe permitir pegar imagen desde portapapeles (`paste` sobre el input/área de chat) y adjuntarla sin pasar por selector de archivos.

Validaciones UX mínimas:

- Mostrar error claro si tipo no permitido.
- Mostrar error claro si excede tamaño.
- Bloquear submit mientras se procesa.

Límites de la etapa:

- Imagen: hasta 5 MB.
- PDF: hasta 10 MB.
- Máximo 3 adjuntos por mensaje.
- Sin persistencia de archivos en servidor o base de datos.
- El mensaje de texto es opcional cuando el turno incluye adjuntos: se permite enviar solo adjuntos sin texto acompañante.

Alcance real de soporte multimodal:

- Imágenes: soporte garantizado para ambos modelos de la lista curada.
- PDF: soporte best-effort; se envía como bloque `document`, pero si el modelo no lo procesa, el turno continúa sin bloqueo ni error duro para el usuario.

Persistencia de contexto de adjuntos en historial:

- Cuando un mensaje de usuario incluye adjuntos, backend guarda metadata no sensible en `agent_messages.structured_payload` (ej. `{type: "attachment_note", count: N, kinds: [...]}`) sin contenido del archivo.
- `partials/message.html` debe renderizar un indicador genérico en historial (ej. `📎 Se enviaron N archivo(s)`) incluso tras recarga de sesión.

## 7) Selector de modelo en chat (objetivo de UI)

Componente objetivo:

- Select visible en toolbar del chat.
- Lista curada inicial fija:
  - `google/gemini-2.5-flash`
  - `openai/gpt-4o-mini`
- Esta lista es la única fuente de verdad del selector mientras no se amplíe en una sesión de documentación dedicada futura.
- Opción por defecto leída desde `profiles.default_model` cuando exista.
- Cambio aplica a mensajes nuevos y se puede persistir por usuario.

Regla explícita:

- El selector solo afecta `create_chat_model()`.
- El modelo de compactación sigue fijo y no seleccionable por usuario.
- El valor recibido desde formulario se valida server-side contra la lista curada; si no coincide, se ignora y se usa default con warning log (sin error duro al usuario).

## 8) Mejoras de render de mensajes

### Botón copiar

- Mostrar botón "Copiar" en cada mensaje del asistente.
- Copia contenido textual renderizado del mensaje.

### Bloques de código con resaltado

- Incluir `highlight.js` por CDN en `base.html` o plantilla de chat.
- Ejecutar resaltado tras cada swap HTMX relevante (`htmx:afterSwap`).
- Mantener HTML limpio y compatible con modo oscuro.

## 9) Onboarding y settings

Estado real actual:

- Onboarding de 4 pasos se mantiene completo en alcance.
- Settings sigue como pantalla de configuración de perfil/agente/herramientas.

No se planifica rediseño de flujo en esta etapa; solo ajustes necesarios para:

- selector de modelo por defecto,
- consistencia con catálogo de tools reducido.

## 10) Inventario de partials relevantes

- `partials/topbar.html`
- `partials/message.html`
- `partials/confirmation.html`
- `partials/session_item.html`
- `partials/settings_save_status.html`

Nuevos partials esperados en esta etapa:

- `partials/chat_attachment_errors.html` (o equivalente)
- `partials/model_selector.html` (o equivalente)
- `partials/session_item_menu.html` (o equivalente para menú de 3 puntos Archivar/Eliminar)
- `partials/message.html` debe soportar render de indicador `attachment_note` en mensajes de usuario con adjuntos.

## 11) Sección HTMX para nuevas capacidades

| Acción nueva | Método + ruta | `hx-target` | `hx-swap` | Resultado esperado |
| --- | --- | --- | --- | --- |
| Enviar chat con adjuntos | `POST /api/chat` | `#messages` | `beforeend` | Mensaje enviado con contenido multimodal |
| Guardar modelo preferido | `POST /settings` (o endpoint dedicado) | `#save-status` | `innerHTML` | Confirmación de guardado |

## 12) Pendientes reales de esta etapa

Se reemplaza la lista antigua de "pendientes de conexión" por estos pendientes actuales:

- Implementar inyección real de memoria en prompt (hoy `memory_injection_node` es no-op).
- Conectar recuperación vectorial real (`match_memories`) con parámetro correcto.
- Completar compactación etapa 2 con LLM y circuit breaker.
- Conectar callback Langfuse al invoke del runtime.
- Reescribir evaluaciones para usar runtime real.
- Incorporar adjuntos multimodales en chat.
- Incorporar selector de modelo con persistencia en `profiles.default_model`.
- Añadir botón copiar y resaltado de código en mensajes.

El desglose operativo por fases vive en `docs/agent_total-plan.md`.
