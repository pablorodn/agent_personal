# UI Design — Agente Personal MVP (Python / Jinja2 + HTMX)

> Contrato visual y de comportamiento de la interfaz web. Refleja el código real en
> `app/templates/` y `app/pages/`. Esta versión incorpora una **topbar horizontal de
> navegación** presente en todas las pantallas autenticadas (chat y settings), que
> resuelve la ausencia de navegación hacia Settings y Logout del MVP inicial.
>
> Fuente de verdad de rutas: tabla de rutas en `docs/technical-brief.md`.
> Esta es la fuente de verdad de UI/partials.

---

## 0. Cómo se relaciona este documento con la demás documentación

Este `ui-design.md` no vive aislado: es una de varias fuentes de verdad que deben mantenerse
sincronizadas. La regla general es **una sola fuente por tema**; los demás documentos referencian,
no duplican.

| Tema | Fuente de verdad | Cómo lo consume `ui-design.md` |
|---|---|---|
| Rutas web/API (método, path) | Tabla de rutas en `docs/technical-brief.md` (§ Tabla completa de rutas) | La §9 de este doc (tabla HTMX) debe usar exactamente esas mismas rutas; si una ruta cambia allí, se actualiza aquí |
| Esquema de datos | `migrations/*.sql` | Los campos que se renderizan (`profile.agent_name`, `session.last_used_at`, estados de `tool_calls`) provienen de ese esquema; este doc no redefine columnas |
| Catálogo de tools y riesgo | `app/tools/catalog.py` (código) + § catálogo del brief | Los badges de riesgo (bajo/medio/alto) y la lista de tools del onboarding y settings se derivan del catálogo, nunca se hardcodean en templates |
| HITL (interrupt/resume, doble ID) | `docs/technical-brief.md` (§ HITL) + `.cursor/.rules/security.mdc` | Los partials `confirmation.html` y `message.html` solo renderizan el `tool_call_id` de auditoría; la mecánica de reanudación se especifica en el brief |
| Seguridad y feature flags | `.cursor/.rules/security.mdc` + brief | La UI nunca expone secretos ni decide ejecución; solo dispara endpoints que aplican la política |
| Variables de entorno | `docs/technical-brief.md` (§ Variables de entorno) + `.env.example` | La UI no lee env vars directamente; las recibe vía contexto de las páginas |

**Contrato de sincronización:** si en este documento cambia una ruta, un `hx-target`, un `hx-swap`,
un nombre de partial o el contrato de un endpoint, hay que reflejarlo en la tabla de rutas del
`technical-brief.md` y, si afecta seguridad o datos, en el `.mdc` o la migración correspondiente.
A la inversa, este documento **se adapta** cuando cambian las fuentes de verdad de datos, tools o rutas.

Orden de lectura recomendado para implementar UI:
1. Tabla de rutas del `technical-brief.md` — qué endpoints existen y qué devuelven.
2. Este `ui-design.md` — cómo se ven y se comportan las pantallas y partials.
3. `app/tools/catalog.py` — qué tools y riesgos renderizar.
4. `migrations/*.sql` — qué campos están disponibles para mostrar.

---

## 1. Tokens de diseño

### Paleta de colores

| Token | Claro | Oscuro | Uso |
|---|---|---|---|
| Background | `#ffffff` | `#0a0a0a` | Fondo de página (definido en `base.html`) |
| Foreground | `#171717` | `#ededed` | Texto principal |
| Primario | `blue-600` | `blue-600` | Botones, links activos, foco |
| Primario hover | `blue-700` | `blue-700` | Hover de botones primarios |
| Superficie | `white` | `neutral-950` | Cards, paneles, inputs |
| Borde | `neutral-200` | `neutral-800` | Bordes de cards y separadores |
| Borde input | `neutral-300` | `neutral-700` | Bordes de campos de formulario |
| Texto secundario | `neutral-500` | `neutral-400` | Subtítulos, placeholders, ayuda |
| Texto muted | `neutral-400` | `neutral-600` | Metadatos, fechas |
| Error | `red-700` / fondo `red-50` | `red-400` / fondo `red-900/30` | Mensajes de error |
| Éxito | `green-600` | `green-400` | Mensajes de éxito |
| Riesgo bajo | `green-800` / fondo `green-100` | `green-400` / fondo `green-900/30` | Badge riesgo bajo |
| Riesgo medio | `yellow-800` / fondo `yellow-100` | `yellow-400` / fondo `yellow-900/30` | Badge riesgo medio |
| Riesgo alto | `red-800` / fondo `red-100` | `red-400` / fondo `red-900/30` | Badge riesgo alto |
| Sesión activa | `blue-700` / fondo `blue-50` | `blue-300` / fondo `blue-900/30` | Item seleccionado en sidebar |
| Mensaje usuario | `blue-600` texto `white` | igual | Burbuja mensaje usuario |
| Mensaje agente | `neutral-100` texto `neutral-900` | `neutral-800` texto `neutral-100` | Burbuja mensaje agente |
| Aprobación HITL | `green-600` hover `green-700` | igual | Botón aprobar |
| Cancelación HITL | `red-600` hover `red-700` | igual | Botón cancelar |
| Warning HITL | `amber-600` | `amber-400` | Aviso de confirmación pendiente |
| Topbar fondo | `white` | `neutral-950` | Barra de navegación superior |
| Topbar borde | `neutral-200` | `neutral-800` | Borde inferior de la topbar |

### Tipografía

| Elemento | Clase Tailwind |
|---|---|
| Fuente base | `Arial, Helvetica, sans-serif` (definido en `body`) |
| Título de página | `text-2xl font-semibold tracking-tight` |
| Título de sección | `text-base font-semibold` / `text-lg font-semibold` |
| Marca en topbar | `text-sm font-semibold` |
| Subtítulo / descripción | `text-sm text-neutral-500` |
| Label de input | `text-sm font-medium` |
| Texto de mensaje | `text-sm leading-relaxed` |
| Texto de ayuda | `text-xs text-neutral-400` |
| Código inline | `font-mono text-sm` |
| Fecha en sidebar | `text-xs font-medium` |

### Espaciado y bordes

| Elemento | Clase Tailwind |
|---|---|
| Radio de botones / inputs | `rounded-md` |
| Radio de cards | `rounded-lg` |
| Radio de badges | `rounded-full` |
| Radio de mensajes | `rounded-lg` |
| Sombra de cards | `shadow-sm` |
| Padding de cards | `p-6` |
| Padding de inputs | `px-3 py-2` |
| Padding de botones primarios | `px-4 py-2` |
| Padding de botones pequeños | `px-3 py-1.5` / `px-2 py-1` |
| Padding de mensajes | `px-4 py-2.5` |
| Altura de la topbar | `h-14` |
| Gap entre elementos de form | `space-y-4` / `space-y-5` |

---

## 2. Layout base — `base.html`

```html
<!DOCTYPE html>
<html lang="es" class="h-full antialiased">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{% block title %}Agente Personal{% endblock %}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>tailwind.config = { darkMode: 'media' };</script>
  <script src="https://unpkg.com/htmx.org@2.0.3" defer></script>
  <style>
    :root { --background: #ffffff; --foreground: #171717; }
    @media (prefers-color-scheme: dark) {
      :root { --background: #0a0a0a; --foreground: #ededed; }
    }
    body {
      background: var(--background);
      color: var(--foreground);
      font-family: Arial, Helvetica, sans-serif;
    }
  </style>
</head>
<body class="min-h-full flex flex-col">
  {% block content %}{% endblock %}
</body>
</html>
```

El modo oscuro se activa automáticamente según `prefers-color-scheme`.

---

## 3. Topbar de navegación — `partials/topbar.html`

Barra horizontal fija en la parte superior de las pantallas autenticadas (`/chat` y
`/settings`). NO aparece en login, signup ni onboarding. Es el componente que provee
acceso a Chat, Settings y cierre de sesión.

```html
<!-- partials/topbar.html -->
<header class="flex h-14 flex-shrink-0 items-center justify-between border-b
               border-neutral-200 px-4 dark:border-neutral-800">

  <!-- Marca / nombre del agente -->
  <div class="flex items-center gap-2">
    <span class="inline-block h-2 w-2 rounded-full bg-blue-600"></span>
    <span class="text-sm font-semibold">{{ agent_name or "Agente Personal" }}</span>
  </div>

  <!-- Navegación -->
  <nav class="flex items-center gap-1">
    <a href="/chat"
       class="rounded-md px-3 py-1.5 text-sm font-medium
              {% if active_nav == 'chat' %}
                bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300
              {% else %}
                text-neutral-600 hover:bg-neutral-100
                dark:text-neutral-400 dark:hover:bg-neutral-800
              {% endif %}">
      Chat
    </a>
    <a href="/settings"
       class="rounded-md px-3 py-1.5 text-sm font-medium
              {% if active_nav == 'settings' %}
                bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300
              {% else %}
                text-neutral-600 hover:bg-neutral-100
                dark:text-neutral-400 dark:hover:bg-neutral-800
              {% endif %}">
      Ajustes
    </a>
    <button hx-post="/logout"
            class="rounded-md px-3 py-1.5 text-sm font-medium text-red-600
                   hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20">
      Salir
    </button>
  </nav>

</header>
```

**Contrato de la topbar:**

- Cada página autenticada pasa `active_nav` (`"chat"` o `"settings"`) y `agent_name` al contexto.
- El botón "Salir" hace `hx-post="/logout"`; el servidor responde con `HX-Redirect: /login`.
- Los links Chat y Ajustes son navegación normal (`<a href>`), no HTMX, porque cambian de página completa.

---

## 4. Pantalla — Login (`GET /login`, `POST /login`)

Pantalla centrada. Ancho `max-w-sm`. Sin topbar.

```html
{% extends "base.html" %}
{% block title %}Iniciar sesión — Agente Personal{% endblock %}
{% block content %}
<main class="flex min-h-screen items-center justify-center px-4">
  <div class="w-full max-w-sm space-y-6">
    <div class="text-center">
      <h1 class="text-2xl font-semibold tracking-tight">Iniciar sesión</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Ingresa a tu cuenta para acceder al agente.
      </p>
    </div>
    {% include "partials/login_form.html" %}
    <p class="text-center text-sm text-neutral-500">
      ¿No tienes cuenta?
      <a href="/signup" class="text-blue-600 hover:underline">Crear cuenta</a>
    </p>
  </div>
</main>
{% endblock %}
```

### Partial — `partials/login_form.html`

Se devuelve solo (sin layout) cuando el login falla, reemplazando `#form-area`.

```html
<form hx-post="/login" hx-target="#form-area" hx-swap="outerHTML"
      id="form-area" class="space-y-4">
  {% if error %}
  <div class="rounded-md bg-red-50 p-3 text-sm text-red-700
              dark:bg-red-900/30 dark:text-red-400">{{ error }}</div>
  {% endif %}
  <div>
    <label for="email" class="block text-sm font-medium mb-1">Correo electrónico</label>
    <input id="email" name="email" type="email" required
           class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2
                  text-sm shadow-sm focus:border-blue-500 focus:outline-none
                  focus:ring-1 focus:ring-blue-500
                  dark:border-neutral-700 dark:bg-neutral-900" />
  </div>
  <div>
    <label for="password" class="block text-sm font-medium mb-1">Contraseña</label>
    <input id="password" name="password" type="password" required
           class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2
                  text-sm shadow-sm focus:border-blue-500 focus:outline-none
                  focus:ring-1 focus:ring-blue-500
                  dark:border-neutral-700 dark:bg-neutral-900" />
  </div>
  <button type="submit"
          class="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium
                 text-white hover:bg-blue-700 disabled:opacity-50">
    Iniciar sesión
  </button>
</form>
```

En éxito, el servidor responde con header `HX-Redirect: /` y setea cookies de sesión.

---

## 5. Pantalla — Signup (`GET /signup`, `POST /signup`)

Idéntica a login en layout. El partial es `partials/signup_form.html`, con
`hx-post="/signup"`, campo de contraseña con `minlength="6"`, botón "Crear cuenta" y
link inferior a `/login`. En éxito responde `HX-Redirect: /onboarding`.

---

## 6. Pantalla — Onboarding (`/onboarding`)

Página centrada `max-w-lg`. Sin topbar (el usuario aún no completó su configuración).
Wizard de 4 pasos. El estado entre pasos se guarda en la sesión del servidor
(`SessionMiddleware` con `SECRET_KEY`), gestionado por `app/services/onboarding_session.py`.

### Contenedor — `onboarding/wizard.html`

```html
{% extends "base.html" %}
{% block title %}Configuración inicial — Agente Personal{% endblock %}
{% block content %}
<main class="flex min-h-screen items-center justify-center px-4 py-12">
  <div class="w-full max-w-lg space-y-6">
    <div class="text-center">
      <h1 class="text-2xl font-semibold tracking-tight">Configura tu agente</h1>
    </div>

    <!-- Indicador de pasos -->
    <nav class="flex items-center justify-center gap-2">
      {% set steps = ["Perfil", "Agente", "Herramientas", "Revisión"] %}
      {% for label in steps %}
        {% set i = loop.index0 %}
        <div class="flex items-center gap-2">
          <div class="flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium
                      {% if i <= current_step %}bg-blue-600 text-white
                      {% else %}bg-neutral-200 text-neutral-500
                        dark:bg-neutral-800 dark:text-neutral-400{% endif %}">
            {{ i + 1 }}
          </div>
          <span class="hidden text-sm sm:inline">{{ label }}</span>
          {% if not loop.last %}
            <div class="h-px w-6 bg-neutral-300 dark:bg-neutral-700"></div>
          {% endif %}
        </div>
      {% endfor %}
    </nav>

    <!-- Paso actual (el wizard completo se re-renderiza en cada navegación) -->
    <div class="rounded-lg border border-neutral-200 bg-white p-6 shadow-sm
                dark:border-neutral-800 dark:bg-neutral-950">
      {% include step_partial %}
    </div>

    <!-- Navegación -->
    <div class="flex justify-between">
      {% if current_step > 0 %}
      <button hx-get="/onboarding/step/{{ current_step - 1 }}"
              hx-target="body" hx-swap="outerHTML"
              class="rounded-md border border-neutral-300 px-4 py-2 text-sm font-medium
                     hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-900">
        Anterior
      </button>
      {% else %}<div></div>{% endif %}

      {% if current_step < 3 %}
      <button hx-post="/onboarding/step/{{ current_step }}"
              hx-target="body" hx-swap="outerHTML"
              hx-include="closest div"
              class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium
                     text-white hover:bg-blue-700">
        Siguiente
      </button>
      {% else %}
      <button hx-post="/onboarding/finish"
              class="rounded-md bg-green-600 px-4 py-2 text-sm font-medium
                     text-white hover:bg-green-700">
        Finalizar y comenzar
      </button>
      {% endif %}
    </div>
  </div>
</main>
{% endblock %}
```

> **Comportamiento real y gaps del onboarding (estado actual del código):**
>
> `GET/POST /onboarding/step/{n}` re-renderizan el wizard completo (`onboarding/wizard.html`)
> con el paso correspondiente; el estado parcial se guarda en la sesión del servidor
> (`SessionMiddleware`) vía `app/services/onboarding_session.py`. El `hx-target` es `body`
> con swap `outerHTML`.
>
> El flujo objetivo es: Perfil → Agente → Herramientas → Revisión → persistir en Supabase.
> Hoy el código tiene tres puntos sin completar que rompen ese flujo de punta a punta y deben
> corregirse (ver también §12):
>
> 1. **El paso 3 (Herramientas) no se persiste.** `POST /onboarding/step/{n}` solo lee
>    `name`, `timezone`, `language`, `agent_name`, `system_prompt` del formulario; nunca lee
>    `enabled_tools`. La selección de tools se pierde antes de llegar a la Revisión.
>    Corrección: leer `enabled_tools` (lista de checkboxes) y guardarla en la sesión de onboarding.
> 2. **`POST /onboarding/finish` no escribe en Supabase.** Hoy solo responde `HX-Redirect: /chat`.
>    Debe: hacer `upsert` en `profiles` (name, timezone, language, agent_name, agent_system_prompt,
>    `onboarding_completed=true`) y `upsert` en `user_tool_settings` (una fila por tool del catálogo,
>    `enabled` según la selección), leyendo el `user_id` del usuario autenticado.
> 3. **`index.py` no enruta al onboarding.** `GET /` debe validar la sesión real y, si
>    `profiles.onboarding_completed` es falso, redirigir a `/onboarding` en vez de a `/chat`.
>    Mientras esto falte, el wizard nunca se muestra de forma natural tras el signup.
>
> Contrato objetivo de `POST /onboarding/finish`: persistencia completa + `HX-Redirect: /chat`.

### Pasos

- `onboarding/step_profile.html` — nombre, zona horaria (select de `timezones`), idioma.
- `onboarding/step_agent.html` — nombre del agente (`maxlength=50`), instrucciones (`maxlength=500`).
- `onboarding/step_tools.html` — checkboxes por tool desde `tool_catalog`, con badge de riesgo
  (bajo/medio/alto) y nota de integración requerida.
- `onboarding/step_review.html` — resumen de perfil, agente y tools habilitadas antes de finalizar.

El badge de riesgo usa este mapeo de estilos:

```html
{% set risk_styles = {
  "low":    "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  "medium": "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  "high":   "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
} %}
{% set risk_labels = {"low": "Bajo", "medium": "Medio", "high": "Alto"} %}
```

---

## 7. Pantalla — Chat (`GET /chat`)

Layout: **topbar** arriba, luego fila con sidebar (izquierda) y área de chat (derecha).

```html
{% extends "base.html" %}
{% block title %}Chat — {{ agent_name }}{% endblock %}
{% block content %}
<div class="flex h-screen flex-col">

  <!-- Topbar de navegación -->
  {% include "partials/topbar.html" %}

  <!-- Cuerpo: sidebar + chat -->
  <div class="flex flex-1 overflow-hidden">

    <!-- ───────── SIDEBAR ───────── -->
    <aside id="sidebar"
           class="{{ 'w-64' if sidebar_open else 'w-0' }}
                  flex-shrink-0 overflow-hidden border-r border-neutral-200
                  transition-all dark:border-neutral-800">
      <div class="flex h-full w-64 flex-col">
        <div class="p-3">
          <button hx-post="/api/sessions"
                  hx-target="#session-list" hx-swap="afterbegin"
                  class="w-full rounded-md bg-blue-600 px-3 py-2 text-sm
                         font-medium text-white hover:bg-blue-700">
            + Nueva sesión
          </button>
        </div>
        <nav id="session-list" class="flex-1 space-y-1 overflow-y-auto px-2 pb-3">
          {% for session in sessions %}
            {% include "partials/session_item.html" %}
          {% else %}
          <p class="px-3 py-4 text-xs text-neutral-400">
            No hay sesiones. Crea una nueva.
          </p>
          {% endfor %}
        </nav>
      </div>
    </aside>

    <!-- ───────── ÁREA DE CHAT ───────── -->
    <div class="flex flex-1 flex-col overflow-hidden">

      <!-- Toolbar del chat (toggle sidebar + estado + limpiar) -->
      <div class="flex items-center gap-2 border-b border-neutral-200 px-3 py-2
                  dark:border-neutral-800">
        <button onclick="toggleSidebar()"
                class="rounded-md p-1.5 text-neutral-500 hover:bg-neutral-100
                       dark:hover:bg-neutral-800" title="Sesiones">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"
               viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="3" y1="6" x2="21" y2="6"/>
            <line x1="3" y1="12" x2="21" y2="12"/>
            <line x1="3" y1="18" x2="21" y2="18"/>
          </svg>
        </button>
        <span class="flex-1 truncate text-xs text-neutral-500">
          {% if current_session_id %}Sesión activa{% else %}Sin sesión{% endif %}
        </span>
        {% if current_session_id %}
        <button hx-post="/api/sessions/{{ current_session_id }}/clear"
                hx-target="#messages" hx-swap="innerHTML"
                class="rounded-md px-2 py-1 text-xs text-red-500
                       hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-900/20">
          Limpiar
        </button>
        {% endif %}
      </div>

      <!-- Mensajes -->
      <div id="messages-container" class="flex-1 overflow-y-auto px-4 py-6">
        <div id="messages" class="mx-auto max-w-2xl space-y-4">
          {% include "partials/messages_list.html" %}
        </div>
      </div>

      <!-- Input -->
      <div class="border-t border-neutral-200 px-4 py-3 dark:border-neutral-800">
        {% if has_pending_confirmation %}
        <p class="mx-auto mb-2 max-w-2xl text-center text-xs text-amber-600
                  dark:text-amber-400">
          Aprueba o cancela la acción pendiente antes de continuar.
        </p>
        {% endif %}
        <form id="chat-form" hx-post="/api/chat" hx-target="#messages"
              hx-swap="beforeend"
              hx-on::after-request="scrollToBottom(); this.reset();"
              class="mx-auto flex max-w-2xl gap-2">
          <input type="hidden" name="session_id" value="{{ current_session_id }}" />
          <input id="chat-input" name="message" type="text"
                 placeholder="Escribe tu mensaje..." autocomplete="off"
                 {% if not current_session_id or has_pending_confirmation %}disabled{% endif %}
                 class="flex-1 rounded-md border border-neutral-300 bg-white px-3 py-2
                        text-sm shadow-sm focus:border-blue-500 focus:outline-none
                        focus:ring-1 focus:ring-blue-500 disabled:opacity-50
                        dark:border-neutral-700 dark:bg-neutral-900" />
          <button type="submit" id="send-btn"
                  {% if not current_session_id or has_pending_confirmation %}disabled{% endif %}
                  class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium
                         text-white hover:bg-blue-700 disabled:opacity-50">
            Enviar
          </button>
        </form>
      </div>

    </div>
  </div>
</div>

<script>
  function scrollToBottom() {
    const c = document.getElementById('messages-container');
    if (c) c.scrollTop = c.scrollHeight;
  }
  function toggleSidebar() {
    const s = document.getElementById('sidebar');
    s.classList.toggle('w-0');
    s.classList.toggle('w-64');
  }
  window.addEventListener('load', scrollToBottom);
</script>
{% endblock %}
```

### Partial — `partials/messages_list.html`

```html
{% if not messages %}
<div class="text-center text-sm text-neutral-400 py-20">
  <p class="text-lg font-medium text-neutral-600 dark:text-neutral-300">
    Hola, soy {{ agent_name or "Agente" }}
  </p>
  <p class="mt-1">Escribe un mensaje para comenzar.</p>
</div>
{% endif %}
{% for msg in messages %}
  {% include "partials/message.html" %}
{% endfor %}
```

### Partial — `partials/message.html`

Burbuja de mensaje. Si lleva confirmación HITL pendiente, renderiza los botones
Aprobar/Cancelar. Nota los **dos identificadores**: `tool_call_id` (UUID de auditoría en
`tool_calls.id`) es el que viaja en la confirmación HITL.

```html
<div class="flex {{ 'justify-end' if msg.role == 'user' else 'justify-start' }}">
  <div class="max-w-[80%] rounded-lg px-4 py-2.5 text-sm leading-relaxed
              {{ 'bg-blue-600 text-white' if msg.role == 'user'
                 else 'bg-neutral-100 text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100' }}">
    <p class="whitespace-pre-wrap">{{ msg.content }}</p>
    {% if msg.confirmation %}
      {% if msg.confirmation_status == "pending" %}
        {% include "partials/confirmation.html" %}
      {% elif msg.confirmation_status == "approved" %}
      <p class="mt-2 text-xs font-medium text-green-700 dark:text-green-400">Aprobado</p>
      {% elif msg.confirmation_status == "rejected" %}
      <p class="mt-2 text-xs font-medium text-red-600 dark:text-red-400">Cancelado</p>
      {% endif %}
    {% endif %}
  </div>
</div>
```

### Partial — `partials/confirmation.html`

```html
<div class="mt-3 flex gap-2">
  <button hx-post="/api/chat/confirm"
          hx-vals='{"tool_call_id": "{{ msg.confirmation.tool_call_id }}", "action": "approve"}'
          hx-target="#messages" hx-swap="beforeend"
          hx-on::after-request="scrollToBottom();"
          class="rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium
                 text-white hover:bg-green-700 disabled:opacity-50">
    Aprobar
  </button>
  <button hx-post="/api/chat/confirm"
          hx-vals='{"tool_call_id": "{{ msg.confirmation.tool_call_id }}", "action": "reject"}'
          hx-target="#messages" hx-swap="beforeend"
          hx-on::after-request="scrollToBottom();"
          class="rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium
                 text-white hover:bg-red-700 disabled:opacity-50">
    Cancelar
  </button>
</div>
```

### Partial — `partials/thinking.html`

```html
<div id="thinking-indicator" class="flex justify-start">
  <div class="rounded-lg bg-neutral-100 px-4 py-2.5 text-sm dark:bg-neutral-800">
    <span class="animate-pulse">Pensando...</span>
  </div>
</div>
```

### Partial — `partials/session_item.html`

```html
<button hx-get="/chat/session/{{ session.id }}"
        hx-target="#messages" hx-swap="innerHTML"
        class="w-full rounded-md px-3 py-2 text-left text-sm
               {% if session.id == current_session_id %}
                 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300
               {% else %}
                 text-neutral-600 hover:bg-neutral-50
                 dark:text-neutral-400 dark:hover:bg-neutral-900{% endif %}">
  <div class="truncate font-medium text-xs">
    {{ session.last_used_at | format_session_date }}
  </div>
</button>
```

---

## 8. Pantalla — Settings (`GET /settings`, `POST /settings`)

Layout: **topbar** arriba, contenido centrado `max-w-2xl`.

```html
{% extends "base.html" %}
{% block title %}Ajustes — Agente Personal{% endblock %}
{% block content %}
<div class="min-h-screen flex flex-col">

  {% include "partials/topbar.html" %}

  <main class="mx-auto w-full max-w-2xl px-4 py-8 space-y-8">

    <!-- Perfil -->
    <section class="space-y-4">
      <h2 class="text-base font-semibold">Perfil</h2>
      <div>
        <label class="block text-sm font-medium mb-1">Nombre</label>
        <input type="text" name="name" value="{{ profile.name }}"
               class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2
                      text-sm dark:border-neutral-700 dark:bg-neutral-900" />
      </div>
    </section>

    <!-- Agente -->
    <section class="space-y-4">
      <h2 class="text-base font-semibold">Agente</h2>
      <div>
        <label class="block text-sm font-medium mb-1">Nombre del agente</label>
        <input type="text" name="agent_name" value="{{ profile.agent_name }}" maxlength="50"
               class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2
                      text-sm dark:border-neutral-700 dark:bg-neutral-900" />
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">Instrucciones</label>
        <textarea name="system_prompt" rows="4" maxlength="500"
                  class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2
                         text-sm dark:border-neutral-700 dark:bg-neutral-900">{{ profile.agent_system_prompt }}</textarea>
      </div>
    </section>

    <!-- Herramientas -->
    <section class="space-y-4">
      <h2 class="text-base font-semibold">Herramientas</h2>
      <div class="space-y-2">
        {% for tool in tool_catalog %}
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" name="enabled_tools" value="{{ tool.id }}"
                 {% if tool.id in enabled_tool_ids %}checked{% endif %}
                 class="rounded border-neutral-300" />
          <span>
            <span class="font-medium">{{ tool.display_name }}</span>
            <span class="ml-1 text-neutral-500">— {{ tool.display_description }}</span>
          </span>
        </label>
        {% endfor %}
      </div>
    </section>

    <!-- GitHub -->
    <section class="space-y-4">
      <h2 class="text-base font-semibold">GitHub</h2>
      <div id="github-section">
        {% if github_connected %}
          {% include "partials/github_connected_block.html" %}
        {% else %}
          {% include "partials/github_disconnected_block.html" %}
        {% endif %}
      </div>
    </section>

    <!-- Telegram -->
    <section class="space-y-4">
      <h2 class="text-base font-semibold">Telegram</h2>
      {% if telegram_linked %}
      <p class="text-sm text-green-600">Cuenta de Telegram vinculada.</p>
      {% else %}
      <button hx-post="/api/telegram/generate-code"
              hx-target="#telegram-code-area" hx-swap="innerHTML"
              class="rounded-md border border-neutral-300 px-3 py-1.5 text-sm font-medium
                     hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-900">
        Generar código de vinculación
      </button>
      <div id="telegram-code-area"></div>
      {% endif %}
    </section>

    <!-- Guardar -->
    <div class="flex items-center gap-3">
      <button hx-post="/settings"
              hx-include="[name='name'], [name='agent_name'], [name='system_prompt'], [name='enabled_tools']"
              hx-target="#save-status" hx-swap="innerHTML"
              class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium
                     text-white hover:bg-blue-700">
        Guardar cambios
      </button>
      <span id="save-status" class="text-sm text-green-600"></span>
    </div>

  </main>
</div>
{% endblock %}
```

### Partials de settings

- `partials/github_connected_block.html` — estado conectado con punto verde y botón Desconectar
  (`hx-post="/api/integrations/github/disconnect"`, target `#github-section`, swap `outerHTML`).
- `partials/github_disconnected_block.html` — texto explicativo y link `<a href="/api/integrations/github">Conectar GitHub</a>`.
- `partials/telegram_link_code.html` — muestra el código `/link CODE` y aviso de expiración (10 min).
- `partials/settings_save_status.html` — `<span>Guardado correctamente.</span>`.

---

## 9. Tabla de comportamiento HTMX por pantalla

| Pantalla | Acción | Método + ruta | `hx-target` | `hx-swap` | Respuesta del servidor |
|---|---|---|---|---|---|
| Login | Submit | `POST /login` | `#form-area` | `outerHTML` | `HX-Redirect: /` o partial form con error |
| Signup | Submit | `POST /signup` | `#form-area` | `outerHTML` | `HX-Redirect: /onboarding` o partial con error |
| Topbar | Salir | `POST /logout` | — | — | `HX-Redirect: /login` |
| Onboarding | Avanzar | `POST /onboarding/step/{n}` | `body` | `outerHTML` | Wizard re-renderizado en paso `n+1` |
| Onboarding | Retroceder | `GET /onboarding/step/{n}` | `body` | `outerHTML` | Wizard re-renderizado en paso `n` |
| Onboarding | Finalizar | `POST /onboarding/finish` | — | — | `HX-Redirect: /chat` |
| Chat | Enviar mensaje | `POST /api/chat` | `#messages` | `beforeend` | Partial `message.html` o confirmación HITL |
| Chat | Confirmar HITL | `POST /api/chat/confirm` | `#messages` | `beforeend` | Partial `message.html` con respuesta final |
| Chat | Nueva sesión | `POST /api/sessions` | `#session-list` | `afterbegin` | Partial `session_item.html` |
| Chat | Cambiar sesión | `GET /chat/session/{id}` | `#messages` | `innerHTML` | Lista de partials `message.html` |
| Chat | Limpiar sesión | `POST /api/sessions/{id}/clear` | `#messages` | `innerHTML` | String vacío |
| Chat | Toggle sidebar | — (JS local) | — | — | `toggleSidebar()` en cliente |
| Settings | Guardar | `POST /settings` | `#save-status` | `innerHTML` | Partial `settings_save_status.html` |
| Settings | Desconectar GitHub | `POST /api/integrations/github/disconnect` | `#github-section` | `outerHTML` | Partial `github_disconnected_block.html` |
| Settings | Generar código Telegram | `POST /api/telegram/generate-code` | `#telegram-code-area` | `innerHTML` | Partial `telegram_link_code.html` |

---

## 10. Filtro Jinja2 — `format_session_date`

Registrado en `app/main.py` sobre el entorno de `Jinja2Templates`:

```python
templates.env.filters["format_session_date"] = format_session_date
```

Formatea `last_used_at` (ISO 8601) a algo legible como "5 jun, 14:30".

---

## 11. Inventario de templates

```
app/templates/
├── base.html
├── chat.html
├── settings.html
├── auth/
│   ├── login.html
│   └── signup.html
├── onboarding/
│   ├── wizard.html
│   ├── step_profile.html
│   ├── step_agent.html
│   ├── step_tools.html
│   └── step_review.html
└── partials/
    ├── topbar.html                    ← navegación horizontal (chat + settings)
    ├── login_form.html
    ├── signup_form.html
    ├── messages_list.html
    ├── message.html
    ├── confirmation.html
    ├── thinking.html
    ├── session_item.html
    ├── tool_badge.html
    ├── github_connected_block.html
    ├── github_disconnected_block.html
    ├── telegram_link_code.html
    └── settings_save_status.html
```

---

## 12. Estado de implementación de la UI (gaps conocidos)

Estos puntos están documentados como **pendientes de conexión** entre la capa de páginas
(`app/pages/`) y los datos reales. La UI renderiza, pero algunas páginas usan datos de
marcador en lugar de leer/escribir Supabase:

| Página / archivo | Estado | Qué falta |
|---|---|---|
| `app/pages/index.py` | Parcial | Solo verifica existencia de cookie. Debe validar la sesión real y, según `profiles.onboarding_completed`, redirigir a `/onboarding` (si falta) o `/chat` (si ya completó). |
| `app/pages/onboarding.py` (`POST /step/{n}`) | Parcial | No lee `enabled_tools` del formulario; la selección de herramientas del paso 3 no se guarda en la sesión de onboarding. |
| `app/pages/onboarding.py` (`POST /finish`) | Parcial | No escribe en Supabase. Debe hacer `upsert` en `profiles` (con `onboarding_completed=true`) y en `user_tool_settings` (una fila por tool del catálogo) usando el `user_id` autenticado, antes del `HX-Redirect: /chat`. |
| `app/pages/chat.py` | Parcial | `agent_name` fijo en `"Agente"`; debe leerse de `profiles`. Falta pasar `active_nav="chat"` para la topbar. |
| `app/pages/settings.py` (GET) | Parcial | Devuelve perfil, tools, github y telegram en valores fijos; debe leer de Supabase (`profiles`, `user_tool_settings`, `user_integrations`, `telegram_accounts`). Falta `active_nav="settings"`. |
| `app/pages/settings.py` (POST) | Parcial | Descarta los datos del formulario; debe persistir `profiles` y `user_tool_settings`. |
| `chat.html` / `settings.html` | Pendiente | Montar `partials/topbar.html` (a crear) con `active_nav` y `agent_name` provistos por sus páginas. |

La topbar (`partials/topbar.html`) **aún no existe como archivo**; su especificación visual está en
la §3 de este documento. Debe crearse e incluirse en `chat.html` y `settings.html`.

### Resumen del flujo de onboarding (objetivo end-to-end)

1. Tras signup, `index.py` detecta `onboarding_completed=false` y redirige a `/onboarding`.
2. El usuario recorre los 4 pasos; cada `POST /step/{n}` acumula datos en la sesión del servidor
   (incluyendo `enabled_tools` en el paso 3).
3. El paso 4 (Revisión) muestra el resumen leyendo la sesión de onboarding.
4. `POST /onboarding/finish` persiste todo en Supabase (`profiles` + `user_tool_settings`),
   marca `onboarding_completed=true` y responde `HX-Redirect: /chat`.
5. A partir de ahí, `index.py` enruta directo a `/chat` y `/onboarding` redirige a `/chat`
   si el usuario ya completó el proceso.