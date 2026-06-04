# Technical Brief — Agente Personal MVP con LangGraph + FastAPI + Supabase

> **v2.0** — Reescritura completa del proyecto `10x-builders-agent` en Python.
> El proyecto implementa un **agente personal conversacional** con control operacional explícito:
> el usuario interactúa por web o Telegram, el agente ejecuta herramientas reales sobre sistemas
> externos, y toda acción sensible pasa por aprobación humana (HITL) antes de ejecutarse.
> La arquitectura prioriza control, trazabilidad y seguridad por encima de autonomía máxima del modelo.
> Esta versión reemplaza el stack TypeScript/Next.js por Python/FastAPI manteniendo
> el mismo esquema de base de datos, las mismas integraciones y la misma lógica de negocio.

---

## 1. Título

**10x Builders Agent — Agente Personal MVP (Python)**
Un agente conversacional con sesiones persistentes, herramientas de dominio, aprobación humana
obligatoria para acciones sensibles, scheduler de tareas, memoria de largo plazo y canales web y Telegram.
Frontend en Jinja2 + HTMX con sidebar de sesiones, wizard de onboarding y chat reactivo sin framework JS.

> Este proyecto NO es un wrapper de ChatGPT.
> **El proyecto ES el runtime del agente**: controla el loop, las políticas de riesgo, el estado
> conversacional y la ejecución de herramientas desde código, no desde el modelo.

---

## 2. Resumen ejecutivo

Este proyecto construye un **agente personal MVP** que resuelve el problema central de centralizar
acciones operativas (gestionar GitHub, programar tareas, leer y escribir archivos, ejecutar bash)
desde chat —web y Telegram— sin perder control humano en ningún punto de la ejecución.

Es la migración completa del proyecto original TypeScript a Python. El esquema de Supabase,
las integraciones externas (OpenRouter, Langfuse, GitHub, Telegram) y la lógica del agente
son idénticos. Lo que cambia es el lenguaje, el framework web y el frontend.

### Qué se construye

- Backend API con **FastAPI** — reemplaza las API routes de Next.js.
- Frontend con **Jinja2 + HTMX + Tailwind CSS** — reemplaza React. Sin JavaScript framework.
- Runtime del agente con **LangGraph Python** — mismo grafo, misma lógica, diferente lenguaje.
- Capa de datos con **supabase-py** — mismas queries, mismas tablas, mismo esquema SQL.
- Cifrado OAuth con **cryptography (PyCA)** — AES-256-GCM compatible con tokens ya almacenados.
- Scheduler con **croniter** — reemplaza croner para cálculo de `next_run_at`.
- Telegram con **python-telegram-bot** — webhook, comandos y botones inline.
- Observabilidad con **Langfuse Python SDK** — mismo `CallbackHandler` para LangChain.

### Qué NO cambia

- Las 4 migraciones SQL de Supabase — el esquema es idéntico, no se toca nada.
- Los modelos de IA — mismos modelos por OpenRouter: `gpt-4o-mini`, `gemini-2.5-flash`, `text-embedding-3-small`.
- La lógica de negocio — mismo catálogo de 12 tools, mismas políticas de riesgo, mismo HITL.
- Las variables de entorno — mismos nombres y misma semántica.
- Los checkpoints de LangGraph — `PostgresSaver` Python es compatible con las tablas existentes.

### Capacidades objetivo del MVP

| Capacidad | Estado objetivo |
|---|---|
| Autenticación (registro, login, logout) | Implementar |
| Onboarding wizard 4 pasos | Implementar |
| Chat web multi-sesión con sidebar | Implementar |
| Runtime LangGraph: `compaction → agent → tools` | Implementar |
| Checkpointing stateful con `PostgresSaver` | Implementar |
| HITL con `interrupt()` + `Command(resume=...)` | Implementar |
| 12 tools con política de riesgo declarativa | Implementar |
| GitHub OAuth + 4 tools GitHub | Implementar |
| File tools (read, write, edit) con feature flag | Implementar |
| Bash tool con feature flag y timeout | Implementar |
| `schedule_task` + scheduler cron | Implementar |
| Bot Telegram: webhook, vinculación, sesiones, HITL | Implementar |
| Compaction de contexto (microcompact + LLM) | Implementar |
| Memoria de largo plazo: extracción + embeddings + pgvector | Implementar |
| Inyección de memoria en prompt | Implementar (conectado desde el inicio) |
| Observabilidad Langfuse + OTel | Implementar |
| Evaluaciones automáticas contra dataset Langfuse | Implementar |

---

## 3. Contexto del proyecto

### Problema que resuelve

Un usuario técnico necesita centralizar acciones operativas dispersas —consultar estado de GitHub,
ejecutar comandos limitados, programar tareas recurrentes, leer y modificar archivos— desde una
sola interfaz conversacional, sin perder trazabilidad ni control sobre qué ejecuta el agente en
su nombre. El MVP resuelve esto con un contrato claro:

- El modelo nunca ejecuta una acción sensible sin pausa explícita y aprobación humana.
- Toda ejecución queda auditada en base de datos.
- Las políticas de riesgo viven en código, no en el prompt del modelo.

### Por qué Python

- LangGraph Python tiene paridad completa de features con la versión TypeScript.
- FastAPI es el estándar de facto en Python para APIs async de alta productividad.
- El ecosistema Python para IA (LangChain, Langfuse, supabase-py, cryptography) está maduro.
- Un proceso persistente FastAPI elimina el cold start que existe en el despliegue Vercel/serverless.
- HTMX permite una UI reactiva completa sin necesidad de React ni build toolchain de frontend.

---

## 4. Principio arquitectónico central

```text
agent-personal-py/
  │
  ├── app/
  │     ├── main.py              ← FastAPI: instancia principal, routers, lifespan
  │     ├── config.py            ← Settings desde variables de entorno (pydantic-settings)
  │     ├── dependencies.py      ← FastAPI Dependencies: get_current_user, get_db, get_agent
  │     │
  │     ├── routers/
  │     │     ├── auth.py        ← POST /login, POST /signup, POST /logout,
  │     │     │                     GET /auth/callback
  │     │     ├── chat.py        ← POST /api/chat, POST /api/chat/confirm
  │     │     ├── sessions.py    ← GET /api/sessions, POST /api/sessions,
  │     │     │                     POST /api/sessions/{id}/clear
  │     │     ├── integrations.py← GET /api/integrations/github,
  │     │     │                     GET /api/integrations/github/callback,
  │     │     │                     POST /api/integrations/github/disconnect
  │     │     ├── telegram.py    ← POST /api/telegram/webhook,
  │     │     │                     GET /api/telegram/setup,
  │     │     │                     POST /api/telegram/generate-code
  │     │     └── cron.py        ← POST /api/cron/scheduled-tasks
  │     │
  │     ├── pages/               ← Rutas que devuelven HTML (Jinja2)
  │     │     ├── index.py       ← GET / (redirect según estado de sesión y onboarding)
  │     │     ├── onboarding.py  ← GET /onboarding,
  │     │     │                     GET /onboarding/step/{n},
  │     │     │                     POST /onboarding/step/{n},
  │     │     │                     POST /onboarding/finish
  │     │     ├── chat.py        ← GET /chat, GET /chat/session/{id}
  │     │     └── settings.py    ← GET /settings, POST /settings
  │     │
  │     ├── agent/
  │     │     ├── graph.py       ← run_agent() — entrada principal del runtime
  │     │     ├── state.py       ← AgentState (TypedDict para LangGraph)
  │     │     ├── checkpointer.py← PostgresSaver singleton
  │     │     ├── model.py       ← create_chat_model(), create_compaction_model()
  │     │     ├── embeddings.py  ← generate_embedding() via OpenRouter
  │     │     ├── memory_flush.py← flush_session_memory() post-turno
  │     │     ├── langfuse.py    ← trazas Langfuse + OTel
  │     │     └── nodes/
  │     │           ├── compaction_node.py
  │     │           └── memory_injection_node.py
  │     │
  │     ├── tools/
  │     │     ├── catalog.py     ← TOOL_CATALOG, get_tool_risk(), tool_requires_confirmation()
  │     │     ├── schemas.py     ← Pydantic models por tool (reemplaza schemas Zod)
  │     │     ├── adapters.py    ← build_langchain_tools(), TOOL_HANDLERS
  │     │     ├── with_tracking.py← decorador de auditoría de tool calls
  │     │     ├── bash_exec.py   ← execute_bash()
  │     │     └── file_tools.py  ← execute_read_file(), write_file(), edit_file()
  │     │
  │     ├── db/
  │     │     ├── client.py      ← create_server_client(), create_browser_client()
  │     │     ├── crypto.py      ← encrypt(), decrypt() AES-256-GCM
  │     │     └── queries/
  │     │           ├── profiles.py
  │     │           ├── sessions.py
  │     │           ├── messages.py
  │     │           ├── tool_calls.py
  │     │           ├── tools.py
  │     │           ├── integrations.py
  │     │           ├── telegram.py
  │     │           ├── scheduled_tasks.py
  │     │           └── memories.py
  │     │
  │     └── templates/           ← Jinja2 templates
  │           ├── base.html      ← layout base con Tailwind CDN + HTMX CDN
  │           ├── partials/      ← fragmentos HTML para HTMX (mensajes, sesiones, confirmaciones)
  │           │     ├── message.html
  │           │     ├── session_item.html
  │           │     ├── confirmation.html
  │           │     └── tool_badge.html
  │           ├── auth/
  │           │     ├── login.html
  │           │     └── signup.html
  │           ├── onboarding/
  │           │     ├── wizard.html
  │           │     ├── step_profile.html
  │           │     ├── step_agent.html
  │           │     ├── step_tools.html
  │           │     └── step_review.html
  │           ├── chat.html
  │           └── settings.html
  │
  ├── migrations/                ← Las 4 migraciones SQL de Supabase (sin cambios)
  │     ├── 00001_initial_schema.sql
  │     ├── 00002_session_management.sql
  │     ├── 00003_scheduled_tasks.sql
  │     └── 00004_long_term_memory.sql
  │
  ├── evals/
  │     └── run_faq_experiment.py← Evaluaciones contra dataset Langfuse
  │
  ├── static/                    ← Archivos estáticos (si se necesitan)
  ├── pyproject.toml             ← Dependencias y configuración del proyecto (uv)
  ├── .env.example               ← Variables de entorno de referencia
  └── README.md
```

`POST /api/chat` y `POST /api/chat/confirm` llaman a `run_agent()`.
`POST /api/telegram/webhook` llama a `run_agent()`.
`POST /api/cron/scheduled-tasks` llama a `run_agent(bypass_confirmation=True)`.
**El runtime del agente es siempre el mismo, independientemente del canal de origen.**

### Tabla completa de rutas

| Método + Ruta | Tipo | Devuelve | Descripción |
|---|---|---|---|
| `POST /login` | Página | `HX-Redirect: /` o partial form con error | Procesa credenciales; setea cookies de sesión |
| `POST /signup` | Página | `HX-Redirect: /onboarding` o partial form con error | Registro de usuario |
| `POST /logout` | Página | `HX-Redirect: /login` | Cierra sesión; borra cookies |
| `GET /auth/callback` | Página | Redirect a `/` o `/onboarding` | Intercambio `code → session` de Supabase Auth |
| `GET /onboarding` | Página | HTML completo (paso 0) | Wizard de onboarding inicial |
| `GET /onboarding/step/{n}` | Página | Partial HTML del paso `n` | Navegación hacia atrás en el wizard |
| `POST /onboarding/step/{n}` | Página | Partial HTML del paso `n+1` | Valida y guarda datos del paso actual |
| `POST /onboarding/finish` | Página | `HX-Redirect: /chat` | Persiste perfil y tools; marca `onboarding_completed=true` |
| `GET /chat` | Página | HTML completo | Renderiza chat con sesión activa e historial |
| `GET /chat/session/{id}` | Página | Lista de partials `message.html` | Historial de mensajes de una sesión |
| `GET /settings` | Página | HTML completo | Renderiza ajustes de perfil, agente, tools e integraciones |
| `POST /settings` | Página | `<span>Guardado correctamente.</span>` | Persiste perfil y configuración de tools |
| `POST /api/chat` | API | Partial `message.html` o partial de confirmación HITL | Turno principal del agente |
| `POST /api/chat/confirm` | API | Partial `message.html` con respuesta final | Reanuda grafo con `approve`/`reject` |
| `GET /api/sessions` | API | JSON `{sessions: [...]}` | Lista sesiones activas del usuario |
| `POST /api/sessions` | API | Partial `session_item.html` | Crea sesión nueva; devuelve item para inyectar en sidebar |
| `POST /api/sessions/{id}/clear` | API | String vacío | Limpia mensajes y tool calls de la sesión |
| `GET /api/integrations/github` | API | Redirect a GitHub OAuth | Genera `state`, guarda en cookie HttpOnly |
| `GET /api/integrations/github/callback` | API | Redirect a `/settings?github=connected` | Intercambia code, cifra y persiste token |
| `POST /api/integrations/github/disconnect` | API | Partial del bloque GitHub desconectado | Revoca integración |
| `POST /api/telegram/webhook` | API (S2S) | `{"ok": true}` | Entrada de updates de Telegram; exento del middleware de auth |
| `GET /api/telegram/setup` | API | JSON con resultado de `setWebhook` | Registra URL del webhook en Telegram |
| `POST /api/telegram/generate-code` | API | Partial con código y instrucciones | Genera código de vinculación en `telegram_link_codes` |
| `POST /api/cron/scheduled-tasks` | API (S2S) | JSON con resumen de ejecución | Ejecutor de tareas vencidas; protegido por `CRON_SECRET` |

---

## 5. Stack técnico

| Capa | Tecnología | Versión | Motivo |
|---|---|---|---|
| **Backend / API** | FastAPI | `>=0.115` | Async nativo, Pydantic v2 integrado, documentación automática OpenAPI |
| **Servidor ASGI** | Uvicorn | `>=0.30` | Servidor de producción para FastAPI |
| **Frontend — templates** | Jinja2 | `>=3.1` | Templates HTML server-side; incluido con FastAPI |
| **Frontend — interactividad** | HTMX | `2.x` (CDN) | Reemplaza React: actualizaciones parciales del DOM sin JS manual |
| **Frontend — estilos** | Tailwind CSS | `3.x` (CDN Play) | Misma utilidad que en el proyecto original; CDN para MVP |
| **Runtime agente** | LangGraph Python | `>=0.2` | Mismo grafo, mismo HITL nativo con `interrupt()` y `Command(resume=...)` |
| **LLM / tools** | LangChain Core | `>=0.3` | Nodos, tools y mensajes del grafo |
| **Checkpointing** | langgraph-checkpoint-postgres | `>=1.0` | `PostgresSaver` Python; tablas compatibles con versión TS |
| **Modelo principal** | openai/gpt-4o-mini via OpenRouter | — | `ChatOpenAI` con `base_url` OpenRouter; contexto 128K tokens |
| **Modelo compaction** | google/gemini-2.5-flash via OpenRouter | — | Rápido y económico para summarización mecánica |
| **Modelo embeddings** | openai/text-embedding-3-small via OpenRouter | — | 1536 dimensiones vía endpoint `/v1/embeddings` de OpenRouter |
| **LangChain OpenAI** | langchain-openai | `>=0.2` | Adaptador `ChatOpenAI` para OpenRouter |
| **Base de datos** | supabase-py | `>=2.0` | Cliente async para queries de dominio con RLS |
| **Postgres directo** | asyncpg | `>=0.29` | Conexión directa para `PostgresSaver` (advisory locks) |
| **Validación** | Pydantic v2 | `>=2.7` | Reemplaza Zod + tipos TypeScript; schemas de tools y contratos API |
| **Configuración** | pydantic-settings | `>=2.3` | Settings desde variables de entorno con validación automática |
| **Cifrado OAuth** | cryptography (PyCA) | `>=42` | AES-256-GCM idéntico al `crypto.ts` original; compatible con tokens existentes |
| **HTTP cliente** | httpx | `>=0.27` | Reemplaza `fetch` para calls a GitHub API y OpenRouter embeddings |
| **Scheduler** | croniter | `>=2.0` | Reemplaza croner; cálculo de `next_run_at` con timezone IANA |
| **Telegram** | python-telegram-bot | `>=21` | Webhook, comandos, botones inline y callback queries |
| **Observabilidad** | langfuse | `>=3.0` | Python SDK; mismo `CallbackHandler` para LangChain |
| **OTel** | opentelemetry-sdk | `>=1.25` | Spans para Langfuse vía `LangfuseSpanProcessor` |
| **Gestor de entorno** | uv | latest | Reemplaza npm; gestor moderno de dependencias Python |
| **Sesiones web** | starlette-sessions o itsdangerous | — | Estado del wizard de onboarding y sesión de usuario en cookie firmada |

---

## 6. Frontend — Jinja2 + HTMX en detalle

### Principio de funcionamiento

HTMX extiende HTML con atributos que permiten hacer requests HTTP y reemplazar partes del DOM
sin escribir JavaScript. El servidor devuelve fragmentos HTML parciales (partials) en lugar de JSON.

```html
<!-- Ejemplo: enviar mensaje en el chat -->
<form hx-post="/api/chat"
      hx-target="#messages"
      hx-swap="beforeend"
      hx-disabled-elt="#send-btn, #message-input">
  <input id="message-input" name="message" autocomplete="off" />
  <button id="send-btn" type="submit">Enviar</button>
</form>
```

Cuando el formulario se envía, HTMX hace el POST, el servidor devuelve un fragmento HTML
con el nuevo mensaje, y HTMX lo inyecta al final del `<div id="messages">` sin recargar la página.

### Páginas y su implementación HTMX

**`/login` y `/signup`**
Formularios HTML estándar con `hx-post`. En caso de error el servidor devuelve el mismo formulario
con el mensaje de error inline. En caso de éxito redirige con `HX-Redirect` header.

**`/onboarding` — Wizard de 4 pasos**

El estado entre pasos se guarda en la sesión del servidor (cookie firmada con `itsdangerous`).
Cada paso es un partial HTML que se carga con `hx-get`:

```html
<!-- Navegación entre pasos -->
<div id="wizard-step"
     hx-get="/onboarding/step/2"
     hx-trigger="stepCompleted from:body"
     hx-target="#wizard-step"
     hx-swap="outerHTML">
  <!-- step actual renderizado aquí -->
</div>
```

Al completar un paso, el servidor persiste los datos parciales en la sesión y devuelve el siguiente
partial. En el paso final (Revisión), escribe `profiles` y `user_tool_settings` en Supabase y
marca `onboarding_completed = true`.

**`/chat` — El componente más complejo**

```html
<!-- Layout del chat -->
<div class="flex h-screen">

  <!-- Sidebar de sesiones -->
  <aside id="sidebar"
         hx-get="/api/sessions"
         hx-trigger="load, sessionChanged from:body"
         hx-swap="innerHTML">
  </aside>

  <!-- Área de mensajes -->
  <main>
    <div id="messages">
      <!-- historial cargado en SSR inicial -->
    </div>

    <!-- Input bloqueado mientras hay confirmación pendiente -->
    <div id="input-area">
      <form hx-post="/api/chat"
            hx-target="#messages"
            hx-swap="beforeend"
            hx-on::after-request="this.reset()">
        <input name="message" id="chat-input" />
        <input type="hidden" name="session_id" value="{{ session_id }}" />
        <button type="submit">Enviar</button>
      </form>
    </div>
  </main>

</div>
```

**Flujo de HITL en el frontend:**

Cuando `/api/chat` detecta una confirmación pendiente, en vez de devolver un partial de mensaje
normal, devuelve un partial de confirmación:

```html
<!-- partials/confirmation.html -->
<div id="confirmation-panel" class="...">
  <p>{{ confirmation.message }}</p>
  <div class="flex gap-2">
    <button hx-post="/api/chat/confirm"
            hx-vals='{"tool_call_id": "{{ confirmation.tool_call_id }}", "action": "approve"}'
            hx-target="#messages"
            hx-swap="beforeend"
            hx-on::after-request="htmx.remove('#confirmation-panel')">
      Aprobar
    </button>
    <button hx-post="/api/chat/confirm"
            hx-vals='{"tool_call_id": "{{ confirmation.tool_call_id }}", "action": "reject"}'
            hx-target="#messages"
            hx-swap="beforeend"
            hx-on::after-request="htmx.remove('#confirmation-panel')">
      Cancelar
    </button>
  </div>
</div>
```

El input del chat se bloquea automáticamente mientras el panel de confirmación está presente
usando un observer CSS o `hx-disabled-elt` condicionado desde el servidor.

**`/settings`**

Formularios independientes para perfil, prompt del agente, tools (toggles) e integraciones.
Cada sección usa `hx-put` o `hx-post` para guardar de forma independiente sin recargar la página.

---

## 7. Runtime del agente — LangGraph Python en detalle

### 7.1 Estado del grafo

```python
# app/agent/state.py
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str
    user_id: str
    system_prompt: str
    compaction_count: int
```

`add_messages` es el reducer de LangGraph Python equivalente a `messagesStateReducer` de la versión TS.
Permite eliminar o reemplazar mensajes con `RemoveMessage`.

### 7.2 Entrada y salida de `run_agent()`

```python
# app/agent/graph.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class AgentInput:
    user_id: str
    session_id: str
    system_prompt: str
    db: AsyncClient
    enabled_tools: list[UserToolSetting]
    integrations: list[UserIntegration]
    message: Optional[str] = None            # Nuevo mensaje del usuario
    resume_decision: Optional[str] = None    # "approve" | "reject" — reanudación HITL
    github_token: Optional[str] = None       # Token descifrado solo en runtime servidor
    bypass_confirmation: bool = False        # True en ejecuciones cron (desatendido)

@dataclass
class AgentOutput:
    response: str
    tool_calls: list[str]
    pending_confirmation: Optional[PendingConfirmation] = None

async def run_agent(input: AgentInput) -> AgentOutput:
    ...
```

### 7.3 Grafo y edges

```python
# app/agent/graph.py
from langgraph.graph import StateGraph, START, END

graph = StateGraph(AgentState)
graph.add_node("memory_injection", memory_injection_node)  # conectado desde el inicio
graph.add_node("compaction", compaction_node)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_executor_node)

graph.add_edge(START, "memory_injection")
graph.add_edge("memory_injection", "compaction")
graph.add_edge("compaction", "agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
graph.add_edge("tools", "compaction")

checkpointer = await get_checkpointer()
app = graph.compile(checkpointer=checkpointer)
```

**Diferencia con la versión TS:** el nodo `memory_injection` se conecta desde el inicio
(en la versión TS estaba comentado). El grafo completo es:
`START → memory_injection → compaction → agent → tools → compaction → ... → END`

`MAX_TOOL_ITERATIONS = 6` — misma protección contra loops infinitos.

### 7.4 Nodo `agent`

```python
async def agent_node(state: AgentState, config: RunnableConfig) -> dict:
    from zoneinfo import ZoneInfo
    from datetime import datetime

    current_date = datetime.now(ZoneInfo("America/Bogota")).strftime(
        "%A, %d de %B de %Y, %H:%M"
    )
    system_prompt_with_date = (
        f"{state['system_prompt']}\n\nFecha y hora actual: {current_date} (hora Colombia)."
    )
    response = await model_with_tools.ainvoke(
        [SystemMessage(content=system_prompt_with_date)] + state["messages"],
        config
    )
    return {"messages": [response]}
```

### 7.5 HITL — `interrupt()` y `Command(resume=...)`

```python
# app/agent/graph.py — dentro de tool_executor_node
from langgraph.types import interrupt, Command

async def tool_executor_node(state: AgentState, config: RunnableConfig) -> dict:
    last_msg = state["messages"][-1]
    results = []

    for tc in last_msg.tool_calls:
        tool_id = tc["name"]

        if tool_requires_confirmation(tool_id):
            if state.get("bypass_confirmation"):
                # Modo desatendido (cron): auto-aprueba sin interrupt
                record = await create_tool_call(db, session_id, tool_id, tc["args"], True)
                await update_tool_call_status(db, record["id"], "approved")
                result = await TOOL_HANDLERS[tool_id](tc["args"], tool_ctx)
                await update_tool_call_status(db, record["id"], "executed", result)
                results.append(ToolMessage(content=json.dumps(result), tool_call_id=tc["id"]))
                continue

            # Modo interactivo: pausa el grafo
            record = await find_or_create_pending_tool_call(db, session_id, tool_id, tc["args"])
            confirm_msg = build_confirmation_message(tool_id, tc["args"])

            # interrupt() pausa aquí; retorna decision en reanudación
            decision = interrupt({
                "tool_call_id": record["id"],
                "tool_name": tool_id,
                "message": confirm_msg,
                "args": tc["args"],
            })

            if decision != "approve":
                await update_tool_call_status(db, record["id"], "rejected")
                results.append(ToolMessage(content="Acción cancelada por el usuario.", tool_call_id=tc["id"]))
                continue

            await update_tool_call_status(db, record["id"], "approved")
            result = await TOOL_HANDLERS[tool_id](tc["args"], tool_ctx)
            await update_tool_call_status(db, record["id"], "executed", result)
            results.append(ToolMessage(content=json.dumps(result), tool_call_id=tc["id"]))
            continue

        # Tool low-risk: ejecuta directo con tracking
        result = await run_with_tracking(tool_id, tc["args"], tool_ctx)
        results.append(ToolMessage(content=json.dumps(result), tool_call_id=tc["id"]))

    return {"messages": results}
```

**Reanudación desde `/api/chat/confirm`:**

```python
# app/routers/chat.py
from langgraph.types import Command

final_state = await app.ainvoke(
    Command(resume=action),  # "approve" | "reject"
    config={"configurable": {"thread_id": session_id}}
)
```

### 7.6 Checkpointing

```python
# app/agent/checkpointer.py
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import asyncpg

_saver: AsyncPostgresSaver | None = None

async def get_checkpointer() -> AsyncPostgresSaver:
    global _saver
    if not _saver:
        conn = await asyncpg.connect(settings.DATABASE_URL)
        _saver = AsyncPostgresSaver(conn)
        await _saver.setup()  # crea tablas de checkpoint (idempotente)
    return _saver
```

Requiere conexión **directa** a Postgres (no pooler de transacciones) por advisory locks.
`thread_id` del configurable de LangGraph se mapea 1:1 con `session_id`.

### 7.7 Compaction de contexto

Misma lógica que la versión TS, migrada a Python:

| Parámetro | Valor |
|---|---|
| `CHARS_PER_TOKEN` | 4 (ratio conservador) |
| `CONTEXT_WINDOW_TOKENS` | 128.000 (gpt-4o-mini) |
| `COMPACTION_THRESHOLD` | 0.8 (80% del context window) |
| `MICROCOMPACT_KEEP_RECENT` | 5 ToolMessages recientes |
| `COMPACTION_TAIL_SIZE` | 10 mensajes verbatim al final |
| `CIRCUIT_BREAKER_LIMIT` | 3 fallos consecutivos |

**Etapa 1 — Microcompact** (sin LLM): reemplaza contenido de `ToolMessage` antiguos por `[compacted]`.
**Etapa 2 — LLM Compaction** (con `google/gemini-2.5-flash`): resume historial en 9 secciones,
preserva cola reciente verbatim. Circuit breaker: tras 3 fallos consecutivos, continúa sin compactar.

### 7.8 Modelos

```python
# app/agent/model.py
from langchain_openai import ChatOpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

def create_chat_model() -> ChatOpenAI:
    return ChatOpenAI(
        model="openai/gpt-4o-mini",
        temperature=0.3,
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL,
        default_headers={"HTTP-Referer": "https://agents.local"},
    )

def create_compaction_model() -> ChatOpenAI:
    return ChatOpenAI(
        model="google/gemini-2.5-flash",
        temperature=0.1,
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL,
        default_headers={"HTTP-Referer": "https://agents.local"},
    )
```

### 7.9 Embeddings

```python
# app/agent/embeddings.py
import httpx

EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

async def generate_embedding(text: str) -> list[float]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://agents.local",
            },
            json={"model": EMBEDDING_MODEL, "input": text, "dimensions": EMBEDDING_DIMENSIONS},
        )
        response.raise_for_status()
        data = response.json()
        embedding = data["data"][0]["embedding"]
        assert len(embedding) == EMBEDDING_DIMENSIONS
        return embedding
```

### 7.10 Memoria de largo plazo

**Extracción post-turno** (`flush_session_memory`): tras cada turno completado sin HITL,
se extrae memoria en background con `asyncio.create_task()` (equivalente al fire-and-forget
de `Promise` en la versión TS):

```python
# app/routers/chat.py
if not result.pending_confirmation:
    asyncio.create_task(
        flush_session_memory(db=db, user_id=user.id, session_id=session_id)
    )
```

**Inyección en prompt** (`memory_injection_node`): conectado desde el inicio del grafo.
Recupera los 8 recuerdos más similares con la RPC `match_memories` de Supabase y los
prepende al `system_prompt` como bloque `[MEMORIA DEL USUARIO]`.

**Tipos de recuerdo:**
- `episodic` — eventos específicos que ocurrieron.
- `semantic` — preferencias, conocimiento durable, datos del usuario.
- `procedural` — flujos de trabajo y rutinas del usuario con el agente.

---

## 8. Capa de datos — supabase-py

### Cliente

```python
# app/db/client.py
from supabase import create_client, AsyncClient

def create_server_client() -> AsyncClient:
    return create_client(
        settings.NEXT_PUBLIC_SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY  # bypasea RLS para operaciones de servidor
    )

def create_browser_client(access_token: str) -> AsyncClient:
    client = create_client(
        settings.NEXT_PUBLIC_SUPABASE_URL,
        settings.NEXT_PUBLIC_SUPABASE_ANON_KEY
    )
    client.postgrest.auth(access_token)  # respeta RLS del usuario autenticado
    return client
```

### Queries tipadas — ejemplo

```python
# app/db/queries/sessions.py
from pydantic import BaseModel

class AgentSession(BaseModel):
    id: str
    user_id: str
    channel: str
    status: str
    budget_tokens_used: int
    budget_tokens_limit: int
    last_used_at: str
    created_at: str

async def get_active_session(
    db: AsyncClient,
    user_id: str,
    channel: str
) -> AgentSession | None:
    result = await (
        db.table("agent_sessions")
        .select("*")
        .eq("user_id", user_id)
        .eq("channel", channel)
        .eq("status", "active")
        .order("last_used_at", desc=True)
        .limit(1)
        .execute()
    )
    return AgentSession(**result.data[0]) if result.data else None
```

### Cifrado OAuth — AES-256-GCM compatible

```python
# app/db/crypto.py
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

IV_LENGTH = 12

def _get_key() -> bytes:
    hex_key = os.environ["OAUTH_ENCRYPTION_KEY"]
    assert len(hex_key) == 64, "OAUTH_ENCRYPTION_KEY must be 64 hex chars (32 bytes)"
    return bytes.fromhex(hex_key)

def encrypt(plaintext: str) -> str:
    key = _get_key()
    iv = os.urandom(IV_LENGTH)
    aesgcm = AESGCM(key)
    # AESGCM.encrypt() devuelve ciphertext + auth_tag concatenados (auth_tag al final, 16 bytes)
    ct_with_tag = aesgcm.encrypt(iv, plaintext.encode(), None)
    ciphertext = ct_with_tag[:-16]
    auth_tag = ct_with_tag[-16:]
    return f"{iv.hex()}:{auth_tag.hex()}:{ciphertext.hex()}"

def decrypt(encoded: str) -> str:
    key = _get_key()
    iv_hex, auth_tag_hex, ciphertext_hex = encoded.split(":")
    iv = bytes.fromhex(iv_hex)
    auth_tag = bytes.fromhex(auth_tag_hex)
    ciphertext = bytes.fromhex(ciphertext_hex)
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(iv, ciphertext + auth_tag, None)
    return plaintext.decode()
```

**Compatibilidad:** el formato `iv:authTag:ciphertext` es idéntico al de `crypto.ts`.
Los tokens GitHub ya almacenados en Supabase se pueden descifrar desde Python sin re-cifrar nada.

---

## 9. Catálogo de herramientas y política de riesgo

Fuente de verdad: `app/tools/catalog.py`

```python
# app/tools/catalog.py
from pydantic import BaseModel
from typing import Literal, Optional

ToolRisk = Literal["low", "medium", "high"]

class ToolDefinition(BaseModel):
    id: str
    name: str
    description: str
    risk: ToolRisk
    requires_integration: Optional[str] = None
    parameters_schema: dict
    display_name: str
    display_description: str

def get_tool_risk(tool_id: str) -> ToolRisk:
    tool = next((t for t in TOOL_CATALOG if t.id == tool_id), None)
    return tool.risk if tool else "high"  # default "high" para tools desconocidas

def tool_requires_confirmation(tool_id: str) -> bool:
    return get_tool_risk(tool_id) in ("medium", "high")
```

### Riesgo bajo (`low`) — Ejecutan sin confirmación

| Tool ID | Display | Descripción | Integración requerida |
|---|---|---|---|
| `get_user_preferences` | Preferencias del usuario | Devuelve configuración y preferencias actuales | — |
| `list_enabled_tools` | Listar herramientas | Lista tools habilitadas del usuario | — |
| `github_list_repos` | GitHub: listar repos | Lista repositorios del usuario (máx. 30, orden `updated`) | `github` |
| `github_list_issues` | GitHub: listar issues | Lista issues de un repo por `owner`, `repo`, `state` | `github` |
| `read_file` | Leer archivo | Lee archivo UTF-8 del filesystem; soporta `offset` y `limit` por línea | `FILE_TOOLS_ENABLED` |

### Riesgo medio (`medium`) — Requieren confirmación humana

| Tool ID | Display | Descripción | Integración requerida |
|---|---|---|---|
| `github_create_issue` | GitHub: crear issue | Crea issue en un repositorio | `github` |
| `github_create_repo` | GitHub: crear repositorio | Crea repositorio nuevo para el usuario | `github` |
| `schedule_task` | Programar tarea | Crea tarea one-time (ISO 8601) o recurrente (cron 5 campos + timezone IANA) | — |

### Riesgo alto (`high`) — Requieren confirmación humana

| Tool ID | Display | Descripción | Guard |
|---|---|---|---|
| `write_file` | Crear archivo | Crea archivo **nuevo**; falla si ya existe | `FILE_TOOLS_ENABLED` |
| `edit_file` | Editar archivo | Reemplaza exactamente **una** ocurrencia de `old_string` por `new_string` | `FILE_TOOLS_ENABLED` |
| `bash` | Bash | Ejecuta comandos bash en el host con timeout; terminal parametrizable | `BASH_TOOL_ENABLED` |

**Regla de disponibilidad:** una tool está disponible para un usuario si y solo si:
1. El usuario la tiene habilitada en `user_tool_settings`.
2. Si requiere integración, esa integración está activa en `user_integrations`.
3. Si requiere feature flag (`FILE_TOOLS_ENABLED`, `BASH_TOOL_ENABLED`), la variable es exactamente `"true"`.

---

## 10. Autenticación — Supabase Auth en FastAPI

### Dependency de autenticación

```python
# app/dependencies.py
from fastapi import Request, HTTPException
from supabase import AsyncClient

async def get_current_user(request: Request) -> dict:
    access_token = request.cookies.get("sb-access-token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    db = create_server_client()
    user_response = await db.auth.get_user(access_token)
    if not user_response.user:
        raise HTTPException(status_code=401, detail="Invalid session")
    return user_response.user
```

### Flujo de login — `POST /login`

HTMX hace `hx-post="/login"`. Si las credenciales son válidas, el servidor responde
con header `HX-Redirect: /` y setea las cookies. Si fallan, devuelve el mismo
formulario con el error inline (el partial reemplaza `#form-area`).

```python
# app/routers/auth.py
@router.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    db = create_server_client()
    result = await db.auth.sign_in_with_password({"email": email, "password": password})
    if result.user:
        response = HTMLResponse(status_code=200)
        response.headers["HX-Redirect"] = "/"
        response.set_cookie("sb-access-token", result.session.access_token, httponly=True, secure=True)
        response.set_cookie("sb-refresh-token", result.session.refresh_token, httponly=True, secure=True)
        return response
    # Error: devuelve el formulario con error para que HTMX lo inyecte en #form-area
    return templates.TemplateResponse("partials/login_form.html", {
        "request": request, "error": "Credenciales inválidas"
    })
```

### Middleware de autenticación

```python
# app/main.py
from starlette.middleware.base import BaseHTTPMiddleware

PUBLIC_PATHS = ["/login", "/signup", "/auth/callback", "/static"]
SERVER_TO_SERVER_PATHS = ["/api/telegram/webhook", "/api/cron/"]

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        is_public = any(path.startswith(p) for p in PUBLIC_PATHS)
        is_s2s = any(path.startswith(p) for p in SERVER_TO_SERVER_PATHS)

        if not is_public and not is_s2s:
            token = request.cookies.get("sb-access-token")
            if not token:
                return RedirectResponse(url="/login")
        return await call_next(request)
```

---

## 11. Flujos end-to-end

### Flujo 1: Chat web con tools y HITL

```text
Browser
  │
  ├── hx-post /api/chat  { message, session_id }   ← HTMX desde #chat-form
  │
  └── app/routers/chat.py  POST /api/chat
        ├── get_current_user(request)           → user
        ├── profiles.select(agent_system_prompt)
        ├── user_tool_settings.select(*)
        ├── user_integrations.select(*)
        ├── decrypt(github_integration.encrypted_tokens) → github_token
        ├── get_or_create_active_session(db, user_id, channel="web")
        ├── touch_session(db, session_id)
        └── run_agent(AgentInput(message=..., user_id=..., session_id=..., ...))
               │
               ├── [TOOL LOW RISK]
               │     → ejecuta directo → ToolMessage → agent responde
               │     → await add_message(db, session_id, "assistant", response_text)
               │     → asyncio.create_task(flush_session_memory(...))
               │     → return partial HTML con el mensaje del asistente
               │
               └── [TOOL MEDIUM/HIGH RISK]
                     → interrupt() pausa el grafo
                     → await add_message(db, session_id, "assistant", confirm_msg,
                                         structured_payload={"type": "pending_confirmation", ...})
                     → return partial HTML con panel de confirmación (botones Aprobar/Cancelar)

  UI inyecta el partial en #messages via HTMX
  Si es confirmación: muestra botones, bloquea input
  │
  ├── hx-post /api/chat/confirm  { tool_call_id, action }   ← HTMX desde partial/confirmation
  │
  └── app/routers/chat.py  POST /api/chat/confirm
        ├── get_pending_tool_call(db, tool_call_id) → valida existencia
        ├── session ownership check → 403 si no coincide user
        └── run_agent(AgentInput(resume_decision=action, ...))
              → app.ainvoke(Command(resume=action), config)
              → [approve] → executed → ToolMessage con resultado real
              → [reject]  → rejected → ToolMessage "cancelado"
              → agent genera respuesta final
              → return partial HTML con respuesta del asistente
```

### Flujo 2: Chat por Telegram

```text
Telegram API
  │
  └── POST /api/telegram/webhook
        ├── valida X-Telegram-Bot-Api-Secret-Token
        ├── parsea update (message o callback_query)
        │
        ├── /link CODE  → telegram_link_codes: vincula telegram_user_id con user_id
        ├── /sessions   → lista sesiones activas
        ├── /new        → crea sesión nueva
        ├── /switch N   → cambia sesión activa
        ├── /clear      → limpia sesión actual
        │
        ├── mensaje normal
        │     → resolve_github_token(db, user_id)
        │     → run_agent(AgentInput(message=text, ...))
        │     → await bot.send_message(chat_id, result.response)
        │
        └── callback_query (botones inline HITL)
              → data: "confirm_approve:{tool_call_id}" | "confirm_reject:{tool_call_id}"
              → run_agent(AgentInput(resume_decision="approve"|"reject", ...))
              → await bot.send_message(chat_id, result.response)
```

### Flujo 3: Scheduler — Tareas programadas

```text
Scheduler externo (Supabase Cron, cron job externo, etc.)
  │
  └── POST /api/cron/scheduled-tasks
        ├── valida Authorization: Bearer <CRON_SECRET>
        ├── claim_due_tasks(db) → SELECT WHERE status='active' AND next_run_at <= now()
        └── por cada tarea vencida:
              ├── upsert agent_session (channel='cron')
              ├── create_task_run(db, task_id, session_id)
              ├── build_agent_context(db, user_id, session_id)
              ├── run_agent(AgentInput(
              │       message=task.prompt,
              │       bypass_confirmation=True,  ← auto-aprueba tools medium/high
              │       ...
              │   ))
              ├── complete_task_run(db, run_id) | fail_task_run(db, run_id, error)
              ├── notify_user_via_telegram(user_id, result)
              └── compute_next_run_at(task)
                    → croniter(task.cron_expr, timezone=task.timezone).get_next(datetime)
                    → actualiza next_run_at (solo tareas recurrentes)
```

### Flujo 4: Memoria de largo plazo

```text
POST /api/chat (turno completado sin HITL)
  │
  └── asyncio.create_task(flush_session_memory(db, user_id, session_id))
        ├── get_session_messages(db, session_id) → historial reciente
        ├── ChatOpenAI(gpt-4o-mini).ainvoke(EXTRACTION_SYSTEM_PROMPT + historial)
        │     → devuelve JSON: [{ "type": "episodic|semantic|procedural", "content": "..." }]
        ├── por cada recuerdo:
        │     ├── generate_embedding(content) → 1536-dim list[float]
        │     └── save_memory(db, user_id, type, content, embedding)
        │           → INSERT INTO memories (user_id, type, content, embedding)
        │
        └── [INYECCIÓN — conectada desde el inicio en esta versión]
              memory_injection_node (primer nodo del grafo):
                → generate_embedding(user_input)
                → match_memories(query_embedding, user_id, limit=8)  [RPC Supabase]
                → ORDER BY embedding <=> query_embedding (cosine similarity)
                → incrementa retrieval_count de los recuerdos usados
                → prepende [MEMORIA DEL USUARIO] al system_prompt
```

---

## 12. Integraciones externas

### GitHub OAuth + REST API

**Flujo de autorización:**
1. `GET /api/integrations/github` → genera `state` con `secrets.token_hex(16)`, guarda en cookie HttpOnly, redirige a GitHub OAuth.
2. `GET /api/integrations/github/callback` → valida `state` contra cookie, intercambia `code` por `access_token` con `httpx`, cifra con AES-256-GCM, persiste en `user_integrations`.
3. `POST /api/integrations/github/disconnect` → marca integración como revocada.

**Scope solicitado:** `repo`.

**Ejecución de tools GitHub:** `httpx.AsyncClient` con headers:
`Authorization: Bearer TOKEN`, `Accept: application/vnd.github+json`, `X-GitHub-Api-Version: 2022-11-28`.

### Telegram Bot

**Setup del webhook:**
`GET /api/telegram/setup` llama a `setWebhook` de la Telegram Bot API apuntando a
`{TELEGRAM_WEBHOOK_BASE_URL}/api/telegram/webhook` con `TELEGRAM_WEBHOOK_SECRET` si está configurado.

**Vinculación de cuenta:**
1. `POST /api/telegram/generate-code` → genera código temporal en `telegram_link_codes` (expira en 10 minutos); devuelve partial HTML con el código y las instrucciones.
2. Usuario envía `/link CODIGO` al bot.
3. El webhook valida el código y vincula `telegram_user_id` + `chat_id` con `user_id`.

**Comandos soportados:** `/link CODE`, `/sessions`, `/new`, `/switch N`, `/clear`.

**Requisito:** Telegram exige HTTPS. En desarrollo local usar `ngrok http 8000`.

---

## 13. Modelo de datos y migraciones Supabase

Las migraciones son idénticas a la versión TypeScript. El esquema no cambia.
Deben aplicarse en orden estricto en el SQL Editor de Supabase.

### Orden de aplicación obligatorio

| Migración | Qué crea |
|---|---|
| `00001_initial_schema.sql` | Tablas base, trigger de perfil, políticas RLS |
| `00002_session_management.sql` | `last_used_at` en sesiones, índice de sesión activa |
| `00003_scheduled_tasks.sql` | Canal `cron`, tablas de scheduler y runs |
| `00004_long_term_memory.sql` | Extensión `pgvector`, tabla `memories`, RPCs de búsqueda semántica |

---

### `00001_initial_schema.sql`

```sql
-- gen_random_uuid() is built into Postgres 13+ (no extension needed)

-- ============================================================
-- profiles (extends Supabase auth.users)
-- ============================================================
create table public.profiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  name        text not null default '',
  timezone    text not null default 'UTC',
  language    text not null default 'es',
  agent_name  text not null default 'Agente',
  agent_system_prompt text not null default 'Eres un asistente útil que ayuda al usuario a gestionar tareas.',
  onboarding_completed boolean not null default false,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "Users can view own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id);

create policy "Users can insert own profile"
  on public.profiles for insert
  with check (auth.uid() = id);

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id)
  values (new.id);
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- ============================================================
-- user_integrations (OAuth tokens per provider)
-- ============================================================
create table public.user_integrations (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null references public.profiles(id) on delete cascade,
  provider         text not null,
  encrypted_tokens text not null default '',
  scopes           text[] not null default '{}',
  status           text not null default 'active' check (status in ('active', 'revoked', 'expired')),
  created_at       timestamptz not null default now(),
  unique (user_id, provider)
);

alter table public.user_integrations enable row level security;

create policy "Users can manage own integrations"
  on public.user_integrations for all
  using (auth.uid() = user_id);

-- ============================================================
-- user_tool_settings (per-user tool enable/config)
-- ============================================================
create table public.user_tool_settings (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.profiles(id) on delete cascade,
  tool_id     text not null,
  enabled     boolean not null default false,
  config_json jsonb not null default '{}',
  unique (user_id, tool_id)
);

alter table public.user_tool_settings enable row level security;

create policy "Users can manage own tool settings"
  on public.user_tool_settings for all
  using (auth.uid() = user_id);

-- ============================================================
-- agent_sessions
-- ============================================================
create table public.agent_sessions (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null references public.profiles(id) on delete cascade,
  channel             text not null default 'web' check (channel in ('web', 'telegram')),
  status              text not null default 'active' check (status in ('active', 'closed')),
  budget_tokens_used  integer not null default 0,
  budget_tokens_limit integer not null default 100000,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

alter table public.agent_sessions enable row level security;

create policy "Users can manage own sessions"
  on public.agent_sessions for all
  using (auth.uid() = user_id);

-- ============================================================
-- agent_messages
-- ============================================================
create table public.agent_messages (
  id                 uuid primary key default gen_random_uuid(),
  session_id         uuid not null references public.agent_sessions(id) on delete cascade,
  role               text not null check (role in ('user', 'assistant', 'tool', 'system')),
  content            text not null default '',
  tool_call_id       text,
  structured_payload jsonb,
  created_at         timestamptz not null default now()
);

alter table public.agent_messages enable row level security;

create policy "Users can manage own messages"
  on public.agent_messages for all
  using (
    exists (
      select 1 from public.agent_sessions s
      where s.id = agent_messages.session_id
        and s.user_id = auth.uid()
    )
  );

-- ============================================================
-- tool_calls
-- ============================================================
create table public.tool_calls (
  id                    uuid primary key default gen_random_uuid(),
  session_id            uuid not null references public.agent_sessions(id) on delete cascade,
  tool_name             text not null,
  arguments_json        jsonb not null default '{}',
  result_json           jsonb,
  status                text not null default 'approved'
    check (status in ('pending_confirmation', 'approved', 'rejected', 'executed', 'failed')),
  requires_confirmation boolean not null default false,
  created_at            timestamptz not null default now(),
  finished_at           timestamptz
);

alter table public.tool_calls enable row level security;

create policy "Users can manage own tool calls"
  on public.tool_calls for all
  using (
    exists (
      select 1 from public.agent_sessions s
      where s.id = tool_calls.session_id
        and s.user_id = auth.uid()
    )
  );

-- ============================================================
-- telegram_accounts
-- ============================================================
create table public.telegram_accounts (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null references public.profiles(id) on delete cascade unique,
  telegram_user_id bigint not null unique,
  chat_id          bigint not null,
  linked_at        timestamptz not null default now()
);

alter table public.telegram_accounts enable row level security;

create policy "Users can manage own telegram account"
  on public.telegram_accounts for all
  using (auth.uid() = user_id);

-- ============================================================
-- telegram_link_codes (one-time codes for linking)
-- ============================================================
create table public.telegram_link_codes (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references public.profiles(id) on delete cascade,
  code       text not null unique,
  used       boolean not null default false,
  expires_at timestamptz not null default (now() + interval '10 minutes'),
  created_at timestamptz not null default now()
);

alter table public.telegram_link_codes enable row level security;

create policy "Users can manage own link codes"
  on public.telegram_link_codes for all
  using (auth.uid() = user_id);
```

---

### `00002_session_management.sql`

```sql
-- Add last_used_at to agent_sessions for tracking current session per channel
ALTER TABLE public.agent_sessions
  ADD COLUMN last_used_at timestamptz NOT NULL DEFAULT now();

-- Backfill existing rows
UPDATE public.agent_sessions SET last_used_at = COALESCE(updated_at, created_at);

-- Index for fast "current session" lookup per user+channel
CREATE INDEX idx_sessions_current
  ON public.agent_sessions (user_id, channel, status, last_used_at DESC);
```

---

### `00003_scheduled_tasks.sql`

```sql
-- ============================================================
-- Extend agent_sessions channel to support cron-triggered runs
-- ============================================================
ALTER TABLE public.agent_sessions
  DROP CONSTRAINT IF EXISTS agent_sessions_channel_check;

ALTER TABLE public.agent_sessions
  ADD CONSTRAINT agent_sessions_channel_check
  CHECK (channel IN ('web', 'telegram', 'cron'));

-- ============================================================
-- scheduled_tasks
-- ============================================================
CREATE TABLE public.scheduled_tasks (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid        NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  prompt        text        NOT NULL,
  schedule_type text        NOT NULL CHECK (schedule_type IN ('one_time', 'recurring')),
  run_at        timestamptz,          -- for one_time: the target execution time
  cron_expr     text,                 -- for recurring: standard 5-field cron expression
  timezone      text        NOT NULL DEFAULT 'UTC',
  status        text        NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'paused', 'completed', 'failed')),
  last_run_at   timestamptz,
  next_run_at   timestamptz,          -- computed; used by the cron runner to find due tasks
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.scheduled_tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own scheduled tasks"
  ON public.scheduled_tasks FOR ALL
  USING (auth.uid() = user_id);

-- Fast lookup for the cron runner (service-role bypasses RLS)
CREATE INDEX idx_scheduled_tasks_due
  ON public.scheduled_tasks (status, next_run_at)
  WHERE status = 'active';

-- ============================================================
-- scheduled_task_runs (audit log per execution)
-- ============================================================
CREATE TABLE public.scheduled_task_runs (
  id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id            uuid        NOT NULL REFERENCES public.scheduled_tasks(id) ON DELETE CASCADE,
  status             text        NOT NULL DEFAULT 'running'
                     CHECK (status IN ('running', 'completed', 'failed')),
  started_at         timestamptz NOT NULL DEFAULT now(),
  finished_at        timestamptz,
  error              text,
  agent_session_id   uuid        REFERENCES public.agent_sessions(id) ON DELETE SET NULL,
  notified           boolean     NOT NULL DEFAULT false,
  notification_error text
);

ALTER TABLE public.scheduled_task_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own task runs"
  ON public.scheduled_task_runs FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.scheduled_tasks t
      WHERE t.id = scheduled_task_runs.task_id
        AND t.user_id = auth.uid()
    )
  );

CREATE INDEX idx_task_runs_task_id
  ON public.scheduled_task_runs (task_id, started_at DESC);
```

---

### `00004_long_term_memory.sql`

```sql
-- Enable pgvector extension (may already be enabled in Supabase)
CREATE EXTENSION IF NOT EXISTS vector;

-- Long-term memory store for the agent
CREATE TABLE memories (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  type              TEXT        NOT NULL CHECK (type IN ('episodic', 'semantic', 'procedural')),
  content           TEXT        NOT NULL,
  embedding         vector(1536),
  retrieval_count   INT         NOT NULL DEFAULT 0,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_retrieved_at TIMESTAMPTZ
);

-- IVFFlat index for approximate nearest-neighbor cosine similarity search
-- lists=100 is a reasonable default for up to ~1M rows
CREATE INDEX memories_embedding_idx
  ON memories USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- Index for efficient per-user filtering
CREATE INDEX memories_user_id_idx ON memories (user_id);

-- RPC function used by increment_retrieval_count() in the agent
CREATE OR REPLACE FUNCTION increment_memory_retrieval_count(memory_ids UUID[])
RETURNS VOID
LANGUAGE SQL
AS $$
  UPDATE memories
  SET retrieval_count   = retrieval_count + 1,
      last_retrieved_at = NOW()
  WHERE id = ANY(memory_ids);
$$;

-- RPC function used by search_memories() in the agent
-- Returns rows ordered by cosine similarity (highest first)
CREATE OR REPLACE FUNCTION match_memories(
  query_embedding   vector(1536),
  match_user_id     UUID,
  match_count       INT DEFAULT 8
)
RETURNS TABLE (
  id                UUID,
  type              TEXT,
  content           TEXT,
  retrieval_count   INT,
  similarity        FLOAT
)
LANGUAGE SQL STABLE
AS $$
  SELECT
    id,
    type,
    content,
    retrieval_count,
    1 - (embedding <=> query_embedding) AS similarity
  FROM memories
  WHERE user_id = match_user_id
    AND embedding IS NOT NULL
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;
```

---

## 14. Seguridad por diseño

### Separación de claves

| Variable | Scope | Motivo |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Cliente y servidor | URL pública del proyecto |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Cliente y servidor | Solo operaciones permitidas por RLS |
| `SUPABASE_SERVICE_ROLE_KEY` | Solo servidor | Bypasea RLS; nunca exponer al cliente |
| `DATABASE_URL` | Solo servidor (checkpointer) | Conexión directa para advisory locks |
| `OPENROUTER_API_KEY` | Solo servidor | Llamadas a modelos y embeddings |
| `OAUTH_ENCRYPTION_KEY` | Solo servidor | AES-256-GCM de tokens OAuth |
| `GITHUB_CLIENT_SECRET` | Solo servidor | Intercambio OAuth |
| `TELEGRAM_BOT_TOKEN` | Solo servidor | API de Telegram |
| `TELEGRAM_WEBHOOK_SECRET` | Solo servidor | Validación de origen del webhook |
| `CRON_SECRET` | Solo servidor | Autenticación del runner de cron |

### Feature flags de riesgo (fail-closed)

| Variable | Default | Efecto |
|---|---|---|
| `BASH_TOOL_ENABLED` | no definida | Sin exactamente `"true"`, `bash` falla con error explícito |
| `FILE_TOOLS_ENABLED` | no definida | Sin exactamente `"true"`, file tools fallan con error explícito |

### Autenticación del cron

Si `CRON_SECRET` está definido, el endpoint `POST /api/cron/scheduled-tasks` exige
`Authorization: Bearer <CRON_SECRET>`. **Siempre definir en producción.**

### GitHub OAuth state

`secrets.token_hex(16)` almacenado en cookie `HttpOnly`, `Secure`, `SameSite=lax`, `max_age=600`.
Se elimina tras el callback.

---

## 15. Variables de entorno — Referencia completa

Archivo de referencia: `.env.example` en la raíz del proyecto.

### Obligatorias

| Variable | Descripción |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | URL del proyecto Supabase |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Clave `anon` para cliente y servidor |
| `SUPABASE_SERVICE_ROLE_KEY` | Clave `service_role` — solo servidor |
| `DATABASE_URL` | Conexión **directa** a Postgres (no pooler de transacciones) |
| `OPENROUTER_API_KEY` | Clave OpenRouter para chat, compaction y embeddings |
| `SECRET_KEY` | Clave para firma de cookies de sesión (Starlette sessions) |

### Opcionales por feature

| Variable | Feature | Notas |
|---|---|---|
| `GITHUB_CLIENT_ID` | GitHub OAuth | Sin esto el botón de conectar GitHub falla |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth | Par con `GITHUB_CLIENT_ID` |
| `OAUTH_ENCRYPTION_KEY` | Cifrado de tokens OAuth | Hex de 64 chars (32 bytes) |
| `TELEGRAM_BOT_TOKEN` | Bot de Telegram | Sin esto webhook y setup fallan |
| `TELEGRAM_WEBHOOK_SECRET` | Autenticación del webhook | Recomendado; validado en header `X-Telegram-Bot-Api-Secret-Token` |
| `TELEGRAM_WEBHOOK_BASE_URL` | URL base del webhook | En local: URL pública de ngrok |
| `BASH_TOOL_ENABLED` | Tool `bash` | Exactamente `"true"` para habilitar |
| `BASH_TOOL_CWD` | Tool `bash` | Directorio de trabajo; default: `os.getcwd()` |
| `FILE_TOOLS_ENABLED` | Tools de archivo | Exactamente `"true"` para habilitar |
| `CRON_SECRET` | Endpoint cron | Bearer secret; sin esto el endpoint es público |
| `LANGFUSE_PUBLIC_KEY` | Trazas Langfuse | Sin esto el sistema funciona sin tracing |
| `LANGFUSE_SECRET_KEY` | Trazas Langfuse | Par con `LANGFUSE_PUBLIC_KEY` |

---

## 16. Observabilidad y operación

### Langfuse Python SDK

```python
# app/agent/langfuse.py
from langfuse.callback import CallbackHandler

def create_langfuse_callback(user_id: str, session_id: str, run_name: str) -> CallbackHandler | None:
    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY):
        return None  # fail-open: funciona sin tracing
    return CallbackHandler(
        user_id=user_id,
        session_id=session_id,
        trace_name=run_name,
        tags=["10x-builders-agent"],
    )
```

Tags automáticos por invocación: `["10x-builders-agent", "cron"|"interactive", "resume"|"message"]`.

### Logging estructurado

A diferencia de la versión TypeScript (que usaba `console.error`), esta versión usa
el módulo `logging` de Python configurado con formato JSON para producción:

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        })
```

### Comandos de operación

| Comando | Descripción |
|---|---|
| `uv run uvicorn app.main:app --reload` | Desarrollo local con hot reload |
| `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` | Producción |
| `uv run python -m pytest` | Tests |
| `uv run ruff check .` | Linting |
| `uv run mypy app/` | Type checking |
| `uv run python evals/run_faq_experiment.py` | Evaluaciones contra dataset Langfuse |

---

## 17. Riesgos técnicos

| Riesgo | Severidad | Descripción | Mitigación |
|---|---|---|---|
| `CRON_SECRET` no definido | Alta | Endpoint cron sin autenticación | Definir siempre en producción |
| `bash` sin sandbox | Alta | Sin confinamiento de red ni filesystem más allá de `BASH_TOOL_CWD` | `BASH_TOOL_ENABLED=false` por defecto; HITL obligatorio |
| File tools sin root confinement | Media | Path absoluto o relativo sin restricción de subdirectorio | `FILE_TOOLS_ENABLED=false` por defecto; HITL obligatorio |
| `OAUTH_ENCRYPTION_KEY` sin rotación | Media | Rotar la clave invalida todos los tokens cifrados | Implementar re-cifrado antes de rotar |
| Async consistente | Media | Un nodo síncrono bloqueante congela el event loop de FastAPI | Todos los handlers de tools deben ser `async def`; usar `asyncio.to_thread` para I/O síncrono |
| Chat HTMX con HITL | Media | El diseño de partials para el flujo de confirmación requiere cuidado | Definir y testear el partial `confirmation.html` desde el inicio |
| Gestión de cookies Supabase | Baja | Refresco del `access_token` más verboso que en `@supabase/ssr` | Implementar middleware de refresco automático en `AuthMiddleware` |
| Rate limiting ausente | Baja | `/api/chat`, `/api/telegram/webhook`, `/api/cron` sin rate limit | Añadir `slowapi` (rate limiter para FastAPI) o Nginx/Cloudflare por delante |

---

## 18. Criterio de prioridad de desarrollo

1. **Estructura base** — FastAPI app, configuración `pydantic-settings`, middleware de auth, templates base Jinja2 + HTMX.
2. **Supabase + migraciones** — aplicar las 4 migraciones, cliente Python, queries de dominio.
3. **Auth** — login, signup, logout, callback, cookie management.
4. **Runtime del agente** — `AgentState`, `run_agent()`, checkpointer, modelos, grafo básico sin tools.
5. **Catálogo de tools + handlers** — Pydantic schemas, handlers de tools low-risk, `with_tracking`.
6. **Chat web** — página `/chat`, sidebar de sesiones, flujo básico mensaje → respuesta.
7. **HITL** — `interrupt()`, partial de confirmación, `/api/chat/confirm`, reanudación con `Command(resume=...)`.
8. **Onboarding wizard** — 4 pasos con estado en sesión, persistencia en Supabase.
9. **Settings** — perfil, agent prompt, toggles de tools, integraciones.
10. **GitHub OAuth** — flujo completo + 4 tools GitHub con HITL donde aplica.
11. **Compaction** — microcompact + LLM compaction con circuit breaker.
12. **Memoria** — `flush_session_memory`, embeddings, `memory_injection_node` conectado.
13. **Telegram** — webhook, vinculación, comandos, HITL con botones inline.
14. **Scheduler** — tool `schedule_task`, endpoint cron, `croniter`, notificación Telegram.
15. **Observabilidad** — Langfuse callback, logging estructurado JSON.
16. **Evaluaciones** — `run_faq_experiment.py` contra dataset Langfuse.
17. **Hardening** — rate limiting con `slowapi`, `SECRET_KEY` en producción, `CRON_SECRET` obligatorio.

---

## 19. Definition of Done — Criterios de éxito del MVP

El MVP se considera completamente implementado cuando:

1. Un usuario puede registrarse, completar el onboarding (perfil + agent + tools) y chatear.
2. El runtime ejecuta tools `low` sin fricción dentro del mismo turno conversacional.
3. El runtime interrumpe para tools `medium`/`high` y el usuario puede aprobar o cancelar desde la UI web.
4. La aprobación/cancelación HITL funciona tras un refresh de página (estado persistido en `agent_messages`).
5. GitHub OAuth conecta, persiste token cifrado y las 4 tools GitHub funcionan en el chat.
6. El bot de Telegram recibe mensajes, vincula cuenta, gestiona sesiones y resuelve HITL con botones inline.
7. Una tarea one-time y una recurrente se crean, ejecutan y dejan auditoría en `scheduled_task_runs`.
8. La memoria de largo plazo extrae recuerdos, genera embeddings, los persiste en `memories` y los inyecta en el prompt del agente en el siguiente turno.
9. El servidor arranca sin errores con `uv run uvicorn app.main:app --reload`.
10. `uv run ruff check .` y `uv run mypy app/` pasan sin errores.
11. Las evaluaciones automáticas (`run_faq_experiment.py`) pasan con score aceptable en Langfuse.
