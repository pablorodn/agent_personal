# UI Design — Agente Personal MVP (Python / Jinja2 + HTMX)

Este documento define el contrato visual y HTMX de la app web. Las rutas deben mantenerse alineadas con la tabla de rutas de `docs/technical-brief.md`; el diseño no debe introducir endpoints no documentados en el brief.

> Documento de referencia visual y de componentes para replicar la interfaz original
> del proyecto `10x-builders-agent` (React/Tailwind) en Jinja2 + HTMX + Tailwind CSS CDN.
> Cada sección describe tokens de diseño, estructura HTML, clases Tailwind exactas
> y comportamiento interactivo de cada pantalla.

---

## 1. Tokens de diseño

### Paleta de colores

Extraída del código fuente original (`globals.css` + clases Tailwind en componentes):

| Token | Claro | Oscuro | Uso |
|---|---|---|---|
| Background | `#ffffff` | `#0a0a0a` | Fondo de página |
| Foreground | `#171717` | `#ededed` | Texto principal |
| Primario | `blue-600` (`#2563eb`) | `blue-600` | Botones, links activos, foco |
| Primario hover | `blue-700` | `blue-700` | Hover de botones primarios |
| Superficie | `white` | `neutral-950` | Cards, paneles, inputs |
| Borde | `neutral-200` | `neutral-800` | Bordes de cards e inputs |
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

### Tipografía

| Elemento | Clase Tailwind |
|---|---|
| Fuente base | `font-family: Arial, Helvetica, sans-serif` (definido en `body` del CSS global) |
| Título de página | `text-2xl font-semibold tracking-tight` |
| Título de sección | `text-base font-semibold` o `text-lg font-semibold` |
| Subtítulo / descripción | `text-sm text-neutral-500` |
| Label de input | `text-sm font-medium` |
| Texto de mensaje | `text-sm leading-relaxed` |
| Texto de ayuda | `text-xs text-neutral-400` |
| Código inline | `font-mono text-sm` |
| Fecha en sidebar | `text-xs font-medium` |

### Espaciado y bordes

| Elemento | Clase Tailwind |
|---|---|
| Radio de botones | `rounded-md` |
| Radio de inputs | `rounded-md` |
| Radio de cards | `rounded-lg` |
| Radio de badges | `rounded-full` |
| Radio de mensajes | `rounded-lg` |
| Sombra de cards | `shadow-sm` |
| Padding de cards | `p-6` |
| Padding de inputs | `px-3 py-2` |
| Padding de botones primarios | `px-4 py-2` |
| Padding de botones pequeños | `px-3 py-1.5` o `px-2 py-1` |
| Padding de mensajes | `px-4 py-2.5` |
| Gap entre elementos de form | `space-y-4` o `space-y-5` |

### Tailwind CDN — inclusión en `base.html`

```html
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = {
    darkMode: 'media',
  }
</script>
```

El modo oscuro se activa automáticamente según `prefers-color-scheme`.

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
  <script>tailwind.config = { darkMode: 'media' }</script>
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

---

## 3. Pantalla — Login (`/login`)

### Layout

Pantalla centrada vertical y horizontalmente. Ancho máximo `max-w-sm`. Sin sidebar.

```html
{% extends "base.html" %}
{% block title %}Iniciar sesión — Agente Personal{% endblock %}
{% block content %}
<main class="flex min-h-screen items-center justify-center px-4">
  <div class="w-full max-w-sm space-y-6">

    <!-- Encabezado -->
    <div class="text-center">
      <h1 class="text-2xl font-semibold tracking-tight">Iniciar sesión</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Ingresa a tu cuenta para acceder al agente.
      </p>
    </div>

    <!-- Formulario -->
    <form hx-post="/login"
          hx-target="#form-area"
          hx-swap="outerHTML"
          id="form-area"
          class="space-y-4">

      <!-- Error (se inyecta desde servidor si falla) -->
      {% if error %}
      <div class="rounded-md bg-red-50 p-3 text-sm text-red-700
                  dark:bg-red-900/30 dark:text-red-400">
        {{ error }}
      </div>
      {% endif %}

      <div>
        <label for="email" class="block text-sm font-medium mb-1">
          Correo electrónico
        </label>
        <input id="email" name="email" type="email" required
               class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2
                      text-sm shadow-sm focus:border-blue-500 focus:outline-none
                      focus:ring-1 focus:ring-blue-500
                      dark:border-neutral-700 dark:bg-neutral-900" />
      </div>

      <div>
        <label for="password" class="block text-sm font-medium mb-1">
          Contraseña
        </label>
        <input id="password" name="password" type="password" required
               class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2
                      text-sm shadow-sm focus:border-blue-500 focus:outline-none
                      focus:ring-1 focus:ring-blue-500
                      dark:border-neutral-700 dark:bg-neutral-900" />
      </div>

      <button type="submit"
              class="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium
                     text-white hover:bg-blue-700 disabled:opacity-50
                     htmx-request:opacity-50">
        <span class="htmx-indicator hidden">Ingresando...</span>
        <span>Iniciar sesión</span>
      </button>
    </form>

    <!-- Link a signup -->
    <p class="text-center text-sm text-neutral-500">
      ¿No tienes cuenta?
      <a href="/signup" class="text-blue-600 hover:underline">Crear cuenta</a>
    </p>

  </div>
</main>
{% endblock %}
```

---

## 4. Pantalla — Signup (`/signup`)

Idéntica al login en layout y estilos. Solo cambia el título, el label del botón
y el link inferior apunta a `/login`.

```html
<!-- Diferencias respecto a login -->
<h1 class="text-2xl font-semibold tracking-tight">Crear cuenta</h1>
<p class="mt-1 text-sm text-neutral-500">
  Crea tu cuenta para empezar a usar el agente.
</p>

<!-- Campo contraseña: agrega minlength -->
<input ... type="password" minlength="6" ... />

<!-- Botón -->
<button ...>Crear cuenta</button>

<!-- Link inferior -->
<p class="text-center text-sm text-neutral-500">
  ¿Ya tienes cuenta?
  <a href="/login" class="text-blue-600 hover:underline">Iniciar sesión</a>
</p>
```

---

## 5. Pantalla — Onboarding (`/onboarding`)

### Layout

Página centrada con `max-w-lg`. Sin sidebar. Wizard de 4 pasos con indicador de progreso.

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
          <div class="flex h-8 w-8 items-center justify-center rounded-full
                      text-xs font-medium
                      {% if i <= current_step %}
                        bg-blue-600 text-white
                      {% else %}
                        bg-neutral-200 text-neutral-500
                        dark:bg-neutral-800 dark:text-neutral-400
                      {% endif %}">
            {{ i + 1 }}
          </div>
          <span class="hidden text-sm sm:inline">{{ label }}</span>
          {% if not loop.last %}
            <div class="h-px w-6 bg-neutral-300 dark:bg-neutral-700"></div>
          {% endif %}
        </div>
      {% endfor %}
    </nav>

    <!-- Contenedor del paso actual (se reemplaza con HTMX) -->
    <div id="wizard-step"
         class="rounded-lg border border-neutral-200 bg-white p-6 shadow-sm
                dark:border-neutral-800 dark:bg-neutral-950">
      {% include step_partial %}
    </div>

    <!-- Navegación -->
    <div class="flex justify-between">
      {% if current_step > 0 %}
      <button hx-get="/onboarding/step/{{ current_step - 1 }}"
              hx-target="#wizard-step"
              hx-swap="outerHTML"
              class="rounded-md border border-neutral-300 px-4 py-2 text-sm
                     font-medium hover:bg-neutral-50
                     dark:border-neutral-700 dark:hover:bg-neutral-900">
        Anterior
      </button>
      {% else %}
      <div></div>
      {% endif %}

      {% if current_step < 3 %}
      <button hx-post="/onboarding/step/{{ current_step }}"
              hx-target="#wizard-step"
              hx-swap="outerHTML"
              class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium
                     text-white hover:bg-blue-700">
        Siguiente
      </button>
      {% else %}
      <button hx-post="/onboarding/finish"
              hx-target="body"
              hx-push-url="/chat"
              class="rounded-md bg-green-600 px-4 py-2 text-sm font-medium
                     text-white hover:bg-green-700 disabled:opacity-50">
        Finalizar y comenzar
      </button>
      {% endif %}
    </div>

  </div>
</main>
{% endblock %}
```

### Paso 1 — Perfil (`partials/step_profile.html`)

```html
<div class="space-y-5">
  <div>
    <h2 class="text-lg font-semibold">Tu perfil</h2>
    <p class="text-sm text-neutral-500">Configura tu información básica.</p>
  </div>

  <div>
    <label for="name" class="block text-sm font-medium mb-1">Nombre</label>
    <input id="name" name="name" type="text"
           value="{{ data.name }}" placeholder="Tu nombre"
           class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2
                  text-sm shadow-sm focus:border-blue-500 focus:outline-none
                  focus:ring-1 focus:ring-blue-500
                  dark:border-neutral-700 dark:bg-neutral-900" />
  </div>

  <div>
    <label for="timezone" class="block text-sm font-medium mb-1">Zona horaria</label>
    <select id="timezone" name="timezone"
            class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2
                   text-sm shadow-sm focus:border-blue-500 focus:outline-none
                   focus:ring-1 focus:ring-blue-500
                   dark:border-neutral-700 dark:bg-neutral-900">
      {% for tz in timezones %}
      <option value="{{ tz }}" {% if data.timezone == tz %}selected{% endif %}>{{ tz }}</option>
      {% endfor %}
    </select>
  </div>

  <div>
    <label for="language" class="block text-sm font-medium mb-1">Idioma</label>
    <select id="language" name="language"
            class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2
                   text-sm shadow-sm focus:border-blue-500 focus:outline-none
                   focus:ring-1 focus:ring-blue-500
                   dark:border-neutral-700 dark:bg-neutral-900">
      <option value="es" {% if data.language == "es" %}selected{% endif %}>Español</option>
      <option value="en" {% if data.language == "en" %}selected{% endif %}>English</option>
    </select>
  </div>
</div>
```

### Paso 2 — Agente (`partials/step_agent.html`)

```html
<div class="space-y-5">
  <div>
    <h2 class="text-lg font-semibold">Configura tu agente</h2>
    <p class="text-sm text-neutral-500">Dale un nombre e instrucciones a tu asistente.</p>
  </div>

  <div>
    <label for="agent_name" class="block text-sm font-medium mb-1">
      Nombre del agente
    </label>
    <input id="agent_name" name="agent_name" type="text"
           value="{{ data.agent_name }}" placeholder="p. ej. Jarvis, Asistente, Bot"
           maxlength="50"
           class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2
                  text-sm shadow-sm focus:border-blue-500 focus:outline-none
                  focus:ring-1 focus:ring-blue-500
                  dark:border-neutral-700 dark:bg-neutral-900" />
  </div>

  <div>
    <label for="system_prompt" class="block text-sm font-medium mb-1">
      Instrucciones del sistema
    </label>
    <p class="text-xs text-neutral-400 mb-2">
      Define el comportamiento y personalidad de tu agente. Máximo 500 caracteres.
    </p>
    <textarea id="system_prompt" name="system_prompt"
              rows="5" maxlength="500"
              class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2
                     text-sm shadow-sm focus:border-blue-500 focus:outline-none
                     focus:ring-1 focus:ring-blue-500
                     dark:border-neutral-700 dark:bg-neutral-900">{{ data.agent_system_prompt }}</textarea>
    <p class="mt-1 text-xs text-neutral-400 text-right">
      <span id="prompt-count">{{ data.agent_system_prompt|length }}</span>/500
    </p>
    <script>
      document.getElementById('system_prompt').addEventListener('input', function() {
        document.getElementById('prompt-count').textContent = this.value.length;
      });
    </script>
  </div>
</div>
```

### Paso 3 — Herramientas (`partials/step_tools.html`)

```html
<div class="space-y-5">
  <div>
    <h2 class="text-lg font-semibold">Herramientas</h2>
    <p class="text-sm text-neutral-500">
      Elige qué herramientas puede usar tu agente. Las de riesgo medio o alto
      pedirán confirmación antes de ejecutar.
    </p>
  </div>

  <div class="space-y-3">
    {% for tool in tool_catalog %}
    {% set risk_styles = {
      "low":    "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
      "medium": "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
      "high":   "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
    } %}
    {% set risk_labels = {"low": "Bajo", "medium": "Medio", "high": "Alto"} %}
    {% set enabled = tool.id in data.enabled_tools %}

    <label class="flex items-start gap-3 rounded-lg border p-3 cursor-pointer transition
                  {% if enabled %}
                    border-blue-500 bg-blue-50 dark:bg-blue-950/20
                  {% else %}
                    border-neutral-200 hover:border-neutral-300
                    dark:border-neutral-800 dark:hover:border-neutral-700
                  {% endif %}">
      <input type="checkbox" name="enabled_tools" value="{{ tool.id }}"
             {% if enabled %}checked{% endif %}
             class="mt-0.5 rounded border-neutral-300" />
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <span class="text-sm font-medium">{{ tool.display_name }}</span>
          <span class="inline-block rounded-full px-2 py-0.5 text-xs font-medium
                       {{ risk_styles[tool.risk] }}">
            {{ risk_labels[tool.risk] }}
          </span>
          {% if tool.requires_integration %}
          <span class="text-xs text-neutral-400">requiere {{ tool.requires_integration }}</span>
          {% endif %}
        </div>
        <p class="text-xs text-neutral-500 mt-0.5">{{ tool.display_description }}</p>
      </div>
    </label>
    {% endfor %}
  </div>
</div>
```

### Paso 4 — Revisión (`partials/step_review.html`)

```html
<div class="space-y-5">
  <div>
    <h2 class="text-lg font-semibold">Revisión</h2>
    <p class="text-sm text-neutral-500">Confirma tu configuración antes de comenzar.</p>
  </div>

  <dl class="space-y-4 text-sm">
    <div>
      <dt class="font-medium text-neutral-400">Nombre</dt>
      <dd>{{ data.name or "(sin definir)" }}</dd>
    </div>
    <div>
      <dt class="font-medium text-neutral-400">Zona horaria</dt>
      <dd>{{ data.timezone }}</dd>
    </div>
    <div>
      <dt class="font-medium text-neutral-400">Idioma</dt>
      <dd>{{ "Español" if data.language == "es" else "English" }}</dd>
    </div>

    <div class="border-t border-neutral-200 pt-4 dark:border-neutral-800">
      <dt class="font-medium text-neutral-400">Nombre del agente</dt>
      <dd>{{ data.agent_name }}</dd>
    </div>
    <div>
      <dt class="font-medium text-neutral-400">Instrucciones</dt>
      <dd class="whitespace-pre-wrap rounded bg-neutral-50 p-2 text-xs
                 dark:bg-neutral-900">{{ data.agent_system_prompt }}</dd>
    </div>

    <div class="border-t border-neutral-200 pt-4 dark:border-neutral-800">
      <dt class="font-medium text-neutral-400">
        Herramientas habilitadas ({{ data.enabled_tools|length }})
      </dt>
      <dd>
        {% if data.enabled_tools %}
        <div class="mt-1 flex flex-wrap gap-1">
          {% for tool_id in data.enabled_tools %}
          <span class="inline-block rounded-full bg-blue-100 px-2.5 py-0.5 text-xs
                       font-medium text-blue-700
                       dark:bg-blue-900/30 dark:text-blue-300">
            {{ tool_id }}
          </span>
          {% endfor %}
        </div>
        {% else %}
        <span class="text-neutral-400">Ninguna seleccionada</span>
        {% endif %}
      </dd>
    </div>
  </dl>
</div>
```

---

## 6. Pantalla — Chat (`/chat`)

### Layout general

`flex h-screen` con sidebar colapsable a la izquierda y área de chat a la derecha.

```html
{% extends "base.html" %}
{% block title %}Chat — {{ agent_name }}{% endblock %}
{% block content %}
<div class="flex flex-1 overflow-hidden" style="height: 100vh;">

  <!-- ═══════════════ SIDEBAR ═══════════════ -->
  <aside id="sidebar"
         class="{{ 'w-64' if sidebar_open else 'w-0' }}
                flex-shrink-0 overflow-hidden border-r border-neutral-200
                transition-all dark:border-neutral-800">
    <div class="flex h-full w-64 flex-col">

      <!-- Botón nueva sesión -->
      <div class="p-3">
        <button hx-post="/api/sessions"
                hx-target="#session-list"
                hx-swap="afterbegin"
                class="w-full rounded-md bg-blue-600 px-3 py-2 text-sm
                       font-medium text-white hover:bg-blue-700">
          + Nueva sesión
        </button>
      </div>

      <!-- Lista de sesiones -->
      <nav id="session-list"
           class="flex-1 space-y-1 overflow-y-auto px-2 pb-3">
        {% for session in sessions %}
        <button hx-get="/chat/session/{{ session.id }}"
                hx-target="#messages"
                hx-swap="innerHTML"
                hx-on::after-request="setActiveSession('{{ session.id }}')"
                class="w-full rounded-md px-3 py-2 text-left text-sm
                       {% if session.id == current_session_id %}
                         bg-blue-50 text-blue-700
                         dark:bg-blue-900/30 dark:text-blue-300
                       {% else %}
                         text-neutral-600 hover:bg-neutral-50
                         dark:text-neutral-400 dark:hover:bg-neutral-900
                       {% endif %}">
          <div class="truncate font-medium text-xs">
            {{ session.last_used_at | format_session_date }}
          </div>
        </button>
        {% else %}
        <p class="px-3 py-4 text-xs text-neutral-400">
          No hay sesiones. Crea una nueva.
        </p>
        {% endfor %}
      </nav>

    </div>
  </aside>

  <!-- ═══════════════ ÁREA DE CHAT ═══════════════ -->
  <div class="flex flex-1 flex-col overflow-hidden">

    <!-- Toolbar superior -->
    <div class="flex items-center gap-2 border-b border-neutral-200 px-3 py-2
                dark:border-neutral-800">

      <!-- Botón toggle sidebar -->
      <button onclick="toggleSidebar()"
              class="rounded-md p-1.5 text-neutral-500
                     hover:bg-neutral-100 dark:hover:bg-neutral-800"
              title="Sesiones">
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
              hx-target="#messages"
              hx-swap="innerHTML"
              class="rounded-md px-2 py-1 text-xs text-red-500
                     hover:bg-red-50 hover:text-red-700
                     dark:hover:bg-red-900/20">
        Limpiar
      </button>
      {% endif %}
    </div>

    <!-- Área de mensajes -->
    <div id="messages-container"
         class="flex-1 overflow-y-auto px-4 py-6">
      <div id="messages" class="mx-auto max-w-2xl space-y-4">

        {% if not messages %}
        <!-- Estado vacío -->
        <div class="text-center text-sm text-neutral-400 py-20">
          <p class="text-lg font-medium text-neutral-600 dark:text-neutral-300">
            {% if agent_name %}Hola, soy {{ agent_name }}{% else %}Hola{% endif %}
          </p>
          <p class="mt-1">Escribe un mensaje para comenzar.</p>
        </div>
        {% endif %}

        {% for msg in messages %}
          {% include "partials/message.html" %}
        {% endfor %}

      </div>
    </div>

    <!-- Input area -->
    <div class="border-t border-neutral-200 px-4 py-3 dark:border-neutral-800">

      {% if has_pending_confirmation %}
      <p class="mx-auto mb-2 max-w-2xl text-center text-xs text-amber-600
                dark:text-amber-400">
        Aprueba o cancela la acción pendiente antes de continuar.
      </p>
      {% endif %}

      <form id="chat-form"
            hx-post="/api/chat"
            hx-target="#messages"
            hx-swap="beforeend"
            hx-on::after-request="scrollToBottom(); this.reset();"
            class="mx-auto flex max-w-2xl gap-2">

        <input type="hidden" name="session_id" value="{{ current_session_id }}" />

        <input id="chat-input"
               name="message"
               type="text"
               placeholder="Escribe tu mensaje..."
               autocomplete="off"
               {% if not current_session_id or has_pending_confirmation %}disabled{% endif %}
               class="flex-1 rounded-md border border-neutral-300 bg-white px-3 py-2
                      text-sm shadow-sm focus:border-blue-500 focus:outline-none
                      focus:ring-1 focus:ring-blue-500 disabled:opacity-50
                      dark:border-neutral-700 dark:bg-neutral-900" />

        <button type="submit"
                id="send-btn"
                {% if not current_session_id or has_pending_confirmation %}disabled{% endif %}
                class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium
                       text-white hover:bg-blue-700 disabled:opacity-50
                       htmx-request:opacity-50">
          Enviar
        </button>
      </form>
    </div>

  </div>
</div>

<script>
  function scrollToBottom() {
    const container = document.getElementById('messages-container');
    container.scrollTop = container.scrollHeight;
  }
  function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('w-0');
    sidebar.classList.toggle('w-64');
  }
  function setActiveSession(id) {
    document.querySelector('input[name="session_id"]').value = id;
  }
  // Scroll al fondo en carga inicial
  window.addEventListener('load', scrollToBottom);
</script>
{% endblock %}
```

### Partial — Mensaje (`partials/message.html`)

```html
<div class="flex {{ 'justify-end' if msg.role == 'user' else 'justify-start' }}">
  <div class="max-w-[80%] rounded-lg px-4 py-2.5 text-sm leading-relaxed
              {{ 'bg-blue-600 text-white' if msg.role == 'user'
                 else 'bg-neutral-100 text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100' }}">

    <p class="whitespace-pre-wrap">{{ msg.content }}</p>

    <!-- Panel de confirmación HITL -->
    {% if msg.confirmation %}
      {% if msg.confirmation_status == "pending" %}
      <div class="mt-3 flex gap-2">
        <button hx-post="/api/chat/confirm"
                hx-vals='{"tool_call_id": "{{ msg.confirmation.tool_call_id }}", "action": "approve"}'
                hx-target="#messages"
                hx-swap="beforeend"
                hx-on::after-request="scrollToBottom(); enableChatInput();"
                class="rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium
                       text-white hover:bg-green-700 disabled:opacity-50">
          Aprobar
        </button>
        <button hx-post="/api/chat/confirm"
                hx-vals='{"tool_call_id": "{{ msg.confirmation.tool_call_id }}", "action": "reject"}'
                hx-target="#messages"
                hx-swap="beforeend"
                hx-on::after-request="scrollToBottom(); enableChatInput();"
                class="rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium
                       text-white hover:bg-red-700 disabled:opacity-50">
          Cancelar
        </button>
      </div>
      {% elif msg.confirmation_status == "approved" %}
      <p class="mt-2 text-xs font-medium text-green-700 dark:text-green-400">Aprobado</p>
      {% elif msg.confirmation_status == "rejected" %}
      <p class="mt-2 text-xs font-medium text-red-600 dark:text-red-400">Cancelado</p>
      {% endif %}
    {% endif %}

  </div>
</div>
```

### Partial — Confirmación HITL (`partials/confirmation.html`)

Este partial se renderiza cuando `POST /api/chat` devuelve una interrupción pendiente del grafo. Sus campos provienen 1:1 del dataclass `PendingConfirmation` definido en `docs/technical-brief.md` §7.2. Debe recibir:

| Campo | Uso UI | Fuente |
|---|---|---|
| `tool_call_id` | Valor enviado a `/api/chat/confirm` (identifica el registro de auditoría) | `tool_calls.id` (UUID de DB) |
| `model_tool_call_id` | No se muestra; el servidor lo usa para reconstruir el `ToolMessage` al reanudar | `tc["id"]` del modelo (LangChain) |
| `tool_name` | Título visible de la acción | Catálogo de tools |
| `risk` | Badge visual `medium`/`high` | Política de riesgo (`get_tool_risk`) |
| `args_preview` | Resumen legible de parámetros | Payload sanitizado (`sanitize_args`, sin secretos) |
| `session_id` | Mantener hilo al reanudar | `agent_sessions.id` |

> **Nota sobre los dos IDs:** la UI solo envía `tool_call_id` (el UUID de DB) en `/api/chat/confirm`. El `model_tool_call_id` nunca sale al cliente; el servidor lo recupera desde `tool_calls.model_tool_call_id` (migración `00005`) para emparejar el resultado con la llamada original del modelo. Ver `docs/technical-brief.md` §7.2 y §7.5.

Estados esperados:

- `pending_confirmation`: muestra botones Aprobar/Rechazar.
- `approved`: oculta botones y muestra estado aprobado mientras se reanuda el grafo.
- `rejected`: oculta botones y muestra acción cancelada.
- `failed`: muestra error recuperable sin reintentar automáticamente.

Las acciones deben usar `hx-post="/api/chat/confirm"`, `hx-target="#messages"` y `hx-swap="beforeend"`.

### Partial — Indicador "Pensando" (`partials/thinking.html`)

Se inyecta en `#messages` mientras el servidor procesa la respuesta:

```html
<div id="thinking-indicator" class="flex justify-start">
  <div class="rounded-lg bg-neutral-100 px-4 py-2.5 text-sm dark:bg-neutral-800">
    <span class="animate-pulse">Pensando...</span>
  </div>
</div>
```

Se elimina con `hx-on::after-request="document.getElementById('thinking-indicator')?.remove()"`.

### Partial — Item de sesión nueva (`partials/session_item.html`)

Devuelto por `POST /api/sessions` para inyectar al inicio del sidebar:

```html
<button hx-get="/chat/session/{{ session.id }}"
        hx-target="#messages"
        hx-swap="innerHTML"
        hx-on::after-request="setActiveSession('{{ session.id }}')"
        class="w-full rounded-md px-3 py-2 text-left text-sm
               bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
  <div class="truncate font-medium text-xs">
    {{ session.last_used_at | format_session_date }}
  </div>
</button>
```

---

## 7. Pantalla — Settings (`/settings`)

### Layout

Página con header + contenido centrado. `max-w-2xl`. Sin sidebar.

```html
{% extends "base.html" %}
{% block title %}Ajustes — Agente Personal{% endblock %}
{% block content %}
<div class="min-h-screen">

  <!-- Header -->
  <header class="border-b border-neutral-200 dark:border-neutral-800">
    <div class="mx-auto max-w-2xl px-4 py-4 flex items-center justify-between">
      <h1 class="text-base font-semibold">Ajustes</h1>
      <a href="/chat" class="text-sm text-blue-600 hover:underline">← Volver al chat</a>
    </div>
  </header>

  <main class="mx-auto max-w-2xl px-4 py-8 space-y-8">

    <!-- ── Perfil ── -->
    <section class="space-y-4">
      <h2 class="text-base font-semibold">Perfil</h2>
      <div>
        <label class="block text-sm font-medium mb-1">Nombre</label>
        <input type="text" name="name" value="{{ profile.name }}"
               class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2
                      text-sm dark:border-neutral-700 dark:bg-neutral-900" />
      </div>
    </section>

    <!-- ── Agente ── -->
    <section class="space-y-4">
      <h2 class="text-base font-semibold">Agente</h2>
      <div>
        <label class="block text-sm font-medium mb-1">Nombre del agente</label>
        <input type="text" name="agent_name" value="{{ profile.agent_name }}"
               maxlength="50"
               class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2
                      text-sm dark:border-neutral-700 dark:bg-neutral-900" />
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">Instrucciones</label>
        <textarea name="system_prompt" rows="4" maxlength="500"
                  class="w-full rounded-md border border-neutral-300 bg-white px-3 py-2
                         text-sm dark:border-neutral-700 dark:bg-neutral-900">{{ profile.agent_system_prompt }}</textarea>
        <p class="text-xs text-neutral-400 text-right mt-1">
          {{ profile.agent_system_prompt|length }}/500
        </p>
      </div>
    </section>

    <!-- ── Herramientas ── -->
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

    <!-- ── GitHub ── -->
    <section class="space-y-4">
      <h2 class="text-base font-semibold">GitHub</h2>
      {% if github_connected %}
      <div class="flex items-center justify-between rounded-md border
                  border-neutral-200 p-4 dark:border-neutral-800">
        <div class="flex items-center gap-2">
          <span class="inline-block h-2 w-2 rounded-full bg-green-500"></span>
          <span class="text-sm font-medium text-green-700 dark:text-green-400">Conectado</span>
        </div>
        <button hx-post="/api/integrations/github/disconnect"
                hx-target="#github-section"
                hx-swap="outerHTML"
                class="rounded-md border border-red-300 px-3 py-1.5 text-xs font-medium
                       text-red-600 hover:bg-red-50 disabled:opacity-50
                       dark:border-red-700 dark:text-red-400 dark:hover:bg-red-900/20">
          Desconectar
        </button>
      </div>
      {% else %}
      <div id="github-section" class="space-y-2">
        <p class="text-sm text-neutral-500">
          Conecta tu cuenta de GitHub para que el agente pueda trabajar
          con tus repositorios e issues.
        </p>
        <a href="/api/integrations/github"
           class="inline-block rounded-md bg-neutral-900 px-4 py-2 text-sm
                  font-medium text-white hover:bg-neutral-800
                  dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200">
          Conectar GitHub
        </a>
      </div>
      {% endif %}
    </section>

    <!-- ── Telegram ── -->
    <section class="space-y-4">
      <h2 class="text-base font-semibold">Telegram</h2>
      {% if telegram_linked %}
      <p class="text-sm text-green-600">Cuenta de Telegram vinculada.</p>
      {% else %}
      <div class="space-y-2">
        <p class="text-sm text-neutral-500">
          Vincula tu cuenta de Telegram para usar el agente desde allí.
        </p>
        {% if link_code %}
        <div class="rounded-md bg-neutral-50 p-4 dark:bg-neutral-900">
          <p class="text-sm">
            Envía este código al bot en Telegram:
            <code class="rounded bg-blue-100 px-2 py-0.5 text-sm font-mono
                         font-bold text-blue-700
                         dark:bg-blue-900/30 dark:text-blue-300">
              /link {{ link_code }}
            </code>
          </p>
          <p class="text-xs text-neutral-400 mt-1">Expira en 10 minutos.</p>
        </div>
        {% else %}
        <button hx-post="/api/telegram/generate-code"
                hx-target="#telegram-code-area"
                hx-swap="innerHTML"
                class="rounded-md border border-neutral-300 px-3 py-1.5 text-sm
                       font-medium hover:bg-neutral-50
                       dark:border-neutral-700 dark:hover:bg-neutral-900">
          Generar código de vinculación
        </button>
        <div id="telegram-code-area"></div>
        {% endif %}
      </div>
      {% endif %}
    </section>

    <!-- ── Botón guardar ── -->
    <div class="flex items-center gap-3">
      <button hx-post="/settings"
              hx-include="[name='name'], [name='agent_name'], [name='system_prompt'], [name='enabled_tools']"
              hx-target="#save-status"
              hx-swap="innerHTML"
              class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium
                     text-white hover:bg-blue-700 disabled:opacity-50
                     htmx-request:opacity-50">
        Guardar cambios
      </button>
      <span id="save-status" class="text-sm text-green-600"></span>
    </div>

  </main>
</div>
{% endblock %}
```

El partial de éxito que devuelve `POST /settings`:

```html
<!-- partial devuelto por el servidor tras guardar -->
<span>Guardado correctamente.</span>
```

---

## 8. Filtro Jinja2 — `format_session_date`

Registrar en FastAPI como filtro del entorno Jinja2:

```python
# app/main.py
from datetime import datetime

def format_session_date(date_str: str) -> str:
    d = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    months = ["ene","feb","mar","abr","may","jun",
              "jul","ago","sep","oct","nov","dic"]
    return f"{d.day} {months[d.month-1]}, {d.strftime('%H:%M')}"

templates.env.filters["format_session_date"] = format_session_date
```

---

## 9. Estados UI obligatorios

| Área | Estado | Comportamiento esperado |
|---|---|---|
| Auth | Credenciales inválidas | Re-render del formulario con error inline, sin redirect |
| Auth | Sesión expirada | Redirect a `/login` o partial de sesión expirada si es petición HTMX |
| Onboarding | Validación fallida | Mantener paso actual y mostrar errores por campo |
| Chat | Historial vacío | Mostrar estado vacío con CTA para iniciar conversación |
| Chat | Enviando mensaje | Mostrar `partials/thinking.html` y deshabilitar submit hasta respuesta |
| Chat | HITL pendiente | Mostrar `partials/confirmation.html`; no duplicar tool calls al refrescar |
| Chat | Error del agente | Mostrar mensaje de error recuperable y conservar input del usuario si aplica |
| Chat | Tool habilitada pero flag global apagado | Si una tool (incluso `low`, p. ej. `read_file`) está habilitada por el usuario pero su feature flag (`FILE_TOOLS_ENABLED`/`BASH_TOOL_ENABLED`) no es `"true"`, el agente responde con un mensaje claro de "herramienta no disponible en este entorno"; no se crea `tool_call` ni se intenta ejecutar |
| Settings | Integración desconectada | Mostrar CTA de conexión y ocultar acciones que requieren token |
| Settings | Guardado exitoso | Actualizar `#save-status` sin recargar pantalla |
| Telegram | Código generado | Mostrar código, expiración y pasos de vinculación |

---

## 10. Comportamiento interactivo — resumen de atributos HTMX por pantalla

| Pantalla | Acción | `hx-method` + ruta | `hx-target` | `hx-swap` |
|---|---|---|---|---|
| Login | Submit form | `hx-post="/login"` | `#form-area` | `outerHTML` |
| Signup | Submit form | `hx-post="/signup"` | `#form-area` | `outerHTML` |
| Onboarding | Avanzar paso | `hx-post="/onboarding/step/{n}"` | `#wizard-step` | `outerHTML` |
| Onboarding | Retroceder paso | `hx-get="/onboarding/step/{n}"` | `#wizard-step` | `outerHTML` |
| Onboarding | Finalizar | `hx-post="/onboarding/finish"` | `body` | `outerHTML` |
| Chat | Enviar mensaje | `hx-post="/api/chat"` | `#messages` | `beforeend` |
| Chat | Confirmar HITL | `hx-post="/api/chat/confirm"` | `#messages` | `beforeend` |
| Chat | Nueva sesión | `hx-post="/api/sessions"` | `#session-list` | `afterbegin` |
| Chat | Cambiar sesión | `hx-get="/chat/session/{id}"` | `#messages` | `innerHTML` |
| Chat | Limpiar sesión | `hx-post="/api/sessions/{id}/clear"` | `#messages` | `innerHTML` |
| Settings | Guardar | `hx-post="/settings"` | `#save-status` | `innerHTML` |
| Settings | Desconectar GitHub | `hx-post="/api/integrations/github/disconnect"` | `#github-section` | `outerHTML` |
| Settings | Generar código Telegram | `hx-post="/api/telegram/generate-code"` | `#telegram-code-area` | `innerHTML` |

---

## 11. Respuestas del servidor — qué devuelve cada endpoint para HTMX

| Endpoint | Respuesta HTML |
|---|---|
| `POST /login` (éxito) | Header `HX-Redirect: /` |
| `POST /login` (error) | Mismo `#form-area` con mensaje de error inline |
| `POST /api/chat` (respuesta normal) | Partial `message.html` con `role=assistant` |
| `POST /api/chat` (HITL pendiente) | Partial `message.html` con panel de confirmación |
| `POST /api/chat/confirm` | Partial `message.html` con respuesta final del agente |
| `POST /api/sessions` | Partial `session_item.html` de la sesión nueva |
| `GET /chat/session/{id}` | Lista de partials `message.html` del historial |
| `POST /api/sessions/{id}/clear` | String vacío (limpia `#messages`) |
| `POST /settings` (éxito) | `<span>Guardado correctamente.</span>` |
| `POST /api/telegram/generate-code` | Partial con el código y las instrucciones |
| `POST /api/integrations/github/disconnect` | Partial del bloque GitHub en estado desconectado |
