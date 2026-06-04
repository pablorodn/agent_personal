from typing import Literal

from pydantic import BaseModel

ToolRisk = Literal["low", "medium", "high"]


class ToolDefinition(BaseModel):
    id: str
    name: str
    description: str
    risk: ToolRisk
    cron_safe: bool = False
    requires_integration: str | None = None
    display_name: str
    display_description: str


TOOL_CATALOG: list[ToolDefinition] = [
    ToolDefinition(id="get_user_preferences", name="get_user_preferences", description="Get preferences", risk="low", cron_safe=True, display_name="Preferencias del usuario", display_description="Devuelve configuración actual"),
    ToolDefinition(id="list_enabled_tools", name="list_enabled_tools", description="List enabled tools", risk="low", cron_safe=True, display_name="Listar herramientas", display_description="Lista herramientas activas"),
    ToolDefinition(id="github_list_repos", name="github_list_repos", description="List repos", risk="low", cron_safe=True, requires_integration="github", display_name="GitHub: listar repos", display_description="Lista repositorios"),
    ToolDefinition(id="github_list_issues", name="github_list_issues", description="List issues", risk="low", cron_safe=True, requires_integration="github", display_name="GitHub: listar issues", display_description="Lista issues"),
    ToolDefinition(id="read_file", name="read_file", description="Read file", risk="low", cron_safe=True, display_name="Leer archivo", display_description="Lee archivos UTF-8"),
    ToolDefinition(id="github_create_issue", name="github_create_issue", description="Create issue", risk="medium", display_name="GitHub: crear issue", display_description="Crea issue"),
    ToolDefinition(id="github_create_repo", name="github_create_repo", description="Create repo", risk="medium", display_name="GitHub: crear repositorio", display_description="Crea repo"),
    ToolDefinition(id="schedule_task", name="schedule_task", description="Schedule task", risk="medium", cron_safe=True, display_name="Programar tarea", display_description="Crea una tarea one-time o recurrente"),
    ToolDefinition(id="write_file", name="write_file", description="Create file", risk="high", display_name="Crear archivo", display_description="Crea archivo nuevo"),
    ToolDefinition(id="edit_file", name="edit_file", description="Edit file", risk="high", display_name="Editar archivo", display_description="Reemplaza una ocurrencia"),
    ToolDefinition(id="bash", name="bash", description="Run bash command", risk="high", display_name="Bash", display_description="Ejecuta comando"),
]


def get_tool_definition(tool_id: str) -> ToolDefinition | None:
    return next((tool for tool in TOOL_CATALOG if tool.id == tool_id), None)


def get_tool_risk(tool_id: str) -> ToolRisk:
    tool = get_tool_definition(tool_id)
    return tool.risk if tool else "high"


def tool_requires_confirmation(tool_id: str) -> bool:
    return get_tool_risk(tool_id) in ("medium", "high")


def tool_is_cron_safe(tool_id: str) -> bool:
    tool = get_tool_definition(tool_id)
    return bool(tool and tool.cron_safe)
