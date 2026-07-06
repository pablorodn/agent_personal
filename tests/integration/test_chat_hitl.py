from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

import app.agent.graph as graph_module
from app.agent.graph import AgentInput, run_agent
from app.dependencies import get_current_user_id, get_db
from app.main import app
from app.services.hitl import build_confirmation_message, sanitize_args


def test_sanitize_args_redacts_sensitive_fields():
    out = sanitize_args("bash", {"command": "ls", "token": "secret"})
    assert out["token"] == "***"
    assert out["command"] == "ls"


def test_confirmation_message_contains_tool():
    msg = build_confirmation_message("bash", {"command": "pwd"})
    assert "bash" in msg


def test_chat_page_uses_profile_and_pending_state(
    monkeypatch, patch_auth_middleware, auth_cookie
):
    async def _fake_db():
        return object()

    async def _fake_user_id():
        return "user-1"

    async def _fake_list_sessions(_db, user_id: str, channel: str = "web"):
        _ = (user_id, channel)
        return [SimpleNamespace(id="session-1", last_used_at="2026-06-04T10:00:00+00:00")]

    async def _fake_session(_db, user_id: str, channel: str):
        _ = (user_id, channel)
        return SimpleNamespace(id="session-1")

    async def _fake_touch(_db, session_id: str):
        _ = session_id

    async def _fake_messages(_db, session_id: str):
        _ = session_id
        return []

    async def _fake_profile(_db, user_id: str):
        _ = user_id
        return SimpleNamespace(agent_name="Atlas")

    async def _fake_pending(_db, session_id: str):
        _ = session_id
        return True

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_current_user_id] = _fake_user_id
    monkeypatch.setattr("app.pages.chat.get_or_create_active_session", _fake_session)
    monkeypatch.setattr("app.pages.chat.list_sessions", _fake_list_sessions)
    monkeypatch.setattr("app.pages.chat.touch_session", _fake_touch)
    monkeypatch.setattr("app.pages.chat.get_session_messages", _fake_messages)
    monkeypatch.setattr("app.pages.chat.get_profile", _fake_profile)
    monkeypatch.setattr("app.pages.chat.has_pending_confirmation_for_session", _fake_pending)

    client = TestClient(app)
    response = client.get("/chat", cookies=auth_cookie)
    assert response.status_code == 200
    assert "Atlas" in response.text
    assert "Aprueba o cancela la acción pendiente antes de continuar." in response.text
    assert 'href="/chat"' in response.text
    assert "bg-blue-50 text-blue-700" in response.text
    app.dependency_overrides.clear()


def test_chat_refresh_keeps_visible_history(monkeypatch, patch_auth_middleware, auth_cookie):
    async def _fake_db():
        return object()

    async def _fake_user_id():
        return "user-1"

    async def _fake_session(_db, user_id: str, channel: str):
        _ = (user_id, channel)
        return SimpleNamespace(id="session-1")

    async def _fake_sessions(_db, user_id: str, channel: str = "web"):
        _ = (user_id, channel)
        return [SimpleNamespace(id="session-1", last_used_at="2026-06-04T10:00:00+00:00")]

    async def _fake_messages(_db, session_id: str):
        _ = session_id
        return [SimpleNamespace(role="assistant", content="Historial visible", structured_payload=None)]

    async def _fake_profile(_db, user_id: str):
        _ = user_id
        return SimpleNamespace(agent_name="Atlas")

    async def _fake_pending(_db, session_id: str):
        _ = session_id
        return False

    async def _fake_touch(_db, session_id: str):
        _ = session_id
        return None

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_current_user_id] = _fake_user_id
    monkeypatch.setattr("app.pages.chat.get_or_create_active_session", _fake_session)
    monkeypatch.setattr("app.pages.chat.list_sessions", _fake_sessions)
    monkeypatch.setattr("app.pages.chat.get_session_messages", _fake_messages)
    monkeypatch.setattr("app.pages.chat.get_profile", _fake_profile)
    monkeypatch.setattr("app.pages.chat.has_pending_confirmation_for_session", _fake_pending)
    monkeypatch.setattr("app.pages.chat.touch_session", _fake_touch)

    client = TestClient(app)
    first = client.get("/chat", cookies=auth_cookie)
    second = client.get("/chat", cookies=auth_cookie)
    assert first.status_code == 200
    assert second.status_code == 200
    assert "Historial visible" in second.text
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_hitl_resume_does_not_reexecute_auto_tool_from_same_batch(monkeypatch):
    """Bloque E (H2): regresion contra el bug de replay de LangGraph.

    Un batch con [get_user_preferences (sin confirmacion), write_file (con
    confirmacion)] en el mismo turno del modelo. Antes del split en
    tools_auto/tools_confirm, LangGraph reproducia el nodo interrumpido
    completo desde el inicio en cada Command(resume=...), lo que re-ejecutaba
    get_user_preferences (ya corrida antes de llegar al interrupt() de
    write_file) una segunda vez. Este test usa el grafo real (StateGraph
    compilado por _get_graph_app) con un checkpointer en memoria para
    ejercitar el mecanismo real de interrupt/resume de LangGraph, no solo los
    nodos en aislamiento.
    """
    graph_module._app = None
    try:
        auto_calls = 0
        confirm_calls = 0

        async def _fake_get_user_preferences(_args, _ctx):
            nonlocal auto_calls
            auto_calls += 1
            return {"preferences": {}}

        async def _fake_write_file(_args, _ctx):
            nonlocal confirm_calls
            confirm_calls += 1
            return {"status": "written"}

        monkeypatch.setitem(graph_module.TOOL_HANDLERS, "get_user_preferences", _fake_get_user_preferences)
        monkeypatch.setitem(graph_module.TOOL_HANDLERS, "write_file", _fake_write_file)

        async def _fake_run_with_tracking(**kwargs):
            return await kwargs["handler"](kwargs["args"])

        monkeypatch.setattr(graph_module, "run_with_tracking", _fake_run_with_tracking)

        class _FakeToolCallRecord:
            id = "tool-call-1"

        async def _fake_find_or_create_pending_tool_call(**_kwargs):
            return _FakeToolCallRecord()

        async def _fake_update_tool_call_status(_db, _tool_call_id, _status, _result=None):
            return None

        monkeypatch.setattr(
            graph_module, "find_or_create_pending_tool_call", _fake_find_or_create_pending_tool_call
        )
        monkeypatch.setattr(graph_module, "update_tool_call_status", _fake_update_tool_call_status)

        async def _fake_memory_injection_node(state, config):
            return {}

        monkeypatch.setattr(graph_module, "memory_injection_node", _fake_memory_injection_node)

        model_calls = 0

        async def _fake_ainvoke_chat_with_fallback(_messages, primary_model=None, tool_schemas=None):
            nonlocal model_calls
            model_calls += 1
            if model_calls == 1:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {"id": "tc-auto-1", "name": "get_user_preferences", "args": {}},
                        {
                            "id": "tc-confirm-1",
                            "name": "write_file",
                            "args": {"path": "a.txt", "content": "hi"},
                        },
                    ],
                )
            return AIMessage(content="listo")

        monkeypatch.setattr(graph_module, "ainvoke_chat_with_fallback", _fake_ainvoke_chat_with_fallback)

        shared_checkpointer = InMemorySaver()

        async def _fake_get_checkpointer():
            return shared_checkpointer

        monkeypatch.setattr(graph_module, "get_checkpointer", _fake_get_checkpointer)

        agent_input = AgentInput(
            user_id="user-1",
            session_id="session-hitl-1",
            system_prompt="Eres un asistente util.",
            db=object(),
            enabled_tools=["get_user_preferences", "write_file"],
            message="hola",
        )
        first_result = await run_agent(agent_input)

        assert first_result.pending_confirmation is not None
        assert first_result.pending_confirmation.tool_name == "write_file"
        # get_user_preferences ya debe haber corrido (batch sin confirmacion
        # flusheado antes del interrupt() de write_file).
        assert auto_calls == 1
        assert confirm_calls == 0

        resume_input = AgentInput(
            user_id="user-1",
            session_id="session-hitl-1",
            system_prompt="Eres un asistente util.",
            db=object(),
            enabled_tools=["get_user_preferences", "write_file"],
            resume_decision="approve",
        )
        second_result = await run_agent(resume_input)

        assert second_result.pending_confirmation is None
        assert confirm_calls == 1
        # La asercion clave: get_user_preferences NO se re-ejecuto al reanudar.
        assert auto_calls == 1
    finally:
        graph_module._app = None


@pytest.mark.anyio
async def test_hitl_resume_does_not_reexecute_prior_confirmation_from_same_batch(monkeypatch):
    """Bloque I: regresion contra la re-ejecucion cuando un mismo batch trae
    2+ tool calls que requieren confirmacion. Antes de este fix,
    tool_executor_confirm_node procesaba todas en un for con interrupt()
    secuenciales dentro de la misma invocacion de nodo; el segundo resume
    (aprobando write_file) re-ejecutaba el handler de edit_file... no, al
    reves: aprobar la primera y luego la segunda re-ejecutaba el handler de
    la PRIMERA (ya aprobada) porque LangGraph reproduce el nodo completo desde
    el inicio en cada resume. Con el fix, cada confirmacion se resuelve en un
    Pregel step propio (tool_executor_confirm_node procesa como maximo una por
    invocacion, route_after_confirm decide si hace falta otra vuelta), asi que
    un resume posterior no debe re-tocar una confirmacion ya resuelta.
    """
    graph_module._app = None
    try:
        write_calls = 0
        edit_calls = 0

        async def _fake_write_file(_args, _ctx):
            nonlocal write_calls
            write_calls += 1
            return {"status": "written"}

        async def _fake_edit_file(_args, _ctx):
            nonlocal edit_calls
            edit_calls += 1
            return {"status": "edited"}

        monkeypatch.setitem(graph_module.TOOL_HANDLERS, "write_file", _fake_write_file)
        monkeypatch.setitem(graph_module.TOOL_HANDLERS, "edit_file", _fake_edit_file)

        record_counter = 0

        class _FakeToolCallRecord:
            def __init__(self, record_id):
                self.id = record_id

        async def _fake_find_or_create_pending_tool_call(**_kwargs):
            nonlocal record_counter
            record_counter += 1
            return _FakeToolCallRecord(f"tool-call-{record_counter}")

        async def _fake_update_tool_call_status(_db, _tool_call_id, _status, _result=None):
            return None

        monkeypatch.setattr(
            graph_module, "find_or_create_pending_tool_call", _fake_find_or_create_pending_tool_call
        )
        monkeypatch.setattr(graph_module, "update_tool_call_status", _fake_update_tool_call_status)

        async def _fake_memory_injection_node(state, config):
            return {}

        monkeypatch.setattr(graph_module, "memory_injection_node", _fake_memory_injection_node)

        model_calls = 0

        async def _fake_ainvoke_chat_with_fallback(_messages, primary_model=None, tool_schemas=None):
            nonlocal model_calls
            model_calls += 1
            if model_calls == 1:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "tc-write-1",
                            "name": "write_file",
                            "args": {"path": "a.txt", "content": "hi"},
                        },
                        {
                            "id": "tc-edit-1",
                            "name": "edit_file",
                            "args": {"path": "a.txt", "old_string": "hi", "new_string": "bye"},
                        },
                    ],
                )
            return AIMessage(content="listo")

        monkeypatch.setattr(graph_module, "ainvoke_chat_with_fallback", _fake_ainvoke_chat_with_fallback)

        shared_checkpointer = InMemorySaver()

        async def _fake_get_checkpointer():
            return shared_checkpointer

        monkeypatch.setattr(graph_module, "get_checkpointer", _fake_get_checkpointer)

        agent_input = AgentInput(
            user_id="user-1",
            session_id="session-2confirm-1",
            system_prompt="Eres un asistente util.",
            db=object(),
            enabled_tools=["write_file", "edit_file"],
            message="hola",
        )
        first_result = await run_agent(agent_input)

        assert first_result.pending_confirmation is not None
        assert first_result.pending_confirmation.tool_name == "write_file"
        assert write_calls == 0
        assert edit_calls == 0

        resume_input = AgentInput(
            user_id="user-1",
            session_id="session-2confirm-1",
            system_prompt="Eres un asistente util.",
            db=object(),
            enabled_tools=["write_file", "edit_file"],
            resume_decision="approve",
        )
        second_result = await run_agent(resume_input)

        # write_file ya se ejecuto y ahora el batch pide confirmar edit_file.
        assert second_result.pending_confirmation is not None
        assert second_result.pending_confirmation.tool_name == "edit_file"
        assert write_calls == 1
        assert edit_calls == 0

        third_result = await run_agent(resume_input)

        assert third_result.pending_confirmation is None
        # La asercion clave: aprobar edit_file NO volvio a ejecutar write_file.
        assert write_calls == 1
        assert edit_calls == 1
    finally:
        graph_module._app = None
