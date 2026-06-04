from collections.abc import Awaitable, Callable
from typing import Any

from app.db.queries.scheduled_tasks import create_scheduled_task
from app.services.github_client import GitHubClient
from app.services.scheduler import compute_next_run_at
from app.tools.bash_exec import execute_bash
from app.tools.file_tools import execute_edit_file, execute_read_file, execute_write_file

ToolHandler = Callable[[dict[str, Any], dict[str, Any]], Awaitable[dict[str, Any]]]


async def handle_get_user_preferences(_: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    return {"preferences": ctx.get("profile", {})}


async def handle_list_enabled_tools(_: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    return {"tools": ctx.get("enabled_tools", [])}


async def handle_github_list_repos(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    gh = GitHubClient(ctx["github_token"])
    repos = await gh.list_repos(per_page=args.get("per_page", 30))
    return {"repos": repos}


async def handle_github_list_issues(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    gh = GitHubClient(ctx["github_token"])
    issues = await gh.list_issues(args["owner"], args["repo"], args.get("state", "open"))
    return {"issues": issues}


async def handle_github_create_issue(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    gh = GitHubClient(ctx["github_token"])
    issue = await gh.create_issue(args["owner"], args["repo"], args["title"], args.get("body"))
    return {"issue": issue}


async def handle_github_create_repo(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    gh = GitHubClient(ctx["github_token"])
    repo = await gh.create_repo(args["name"], args.get("private", True))
    return {"repo": repo}


async def handle_read_file(args: dict[str, Any], _: dict[str, Any]) -> dict[str, Any]:
    return {"content": execute_read_file(args["path"], args.get("offset"), args.get("limit"))}


async def handle_write_file(args: dict[str, Any], _: dict[str, Any]) -> dict[str, Any]:
    return {"status": execute_write_file(args["path"], args["content"])}


async def handle_edit_file(args: dict[str, Any], _: dict[str, Any]) -> dict[str, Any]:
    return {"status": execute_edit_file(args["path"], args["old_string"], args["new_string"])}


async def handle_bash(args: dict[str, Any], _: dict[str, Any]) -> dict[str, Any]:
    return await execute_bash(args["command"], args.get("timeout_seconds", 30))


async def handle_schedule_task(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    run_at = args.get("run_at")
    cron_expr = args.get("cron_expr")
    tz = args.get("timezone", "UTC")
    if bool(run_at) == bool(cron_expr):
        return {"error": "Provide exactly one of run_at or cron_expr"}
    if cron_expr and not run_at:
        run_at = compute_next_run_at(cron_expr, tz)
    task = await create_scheduled_task(
        db=ctx["db"],
        user_id=ctx["user_id"],
        prompt=args["prompt"],
        run_at=run_at,
        cron_expr=cron_expr,
        timezone=tz,
    )
    return {"task": task}


TOOL_HANDLERS: dict[str, ToolHandler] = {
    "get_user_preferences": handle_get_user_preferences,
    "list_enabled_tools": handle_list_enabled_tools,
    "github_list_repos": handle_github_list_repos,
    "github_list_issues": handle_github_list_issues,
    "github_create_issue": handle_github_create_issue,
    "github_create_repo": handle_github_create_repo,
    "read_file": handle_read_file,
    "write_file": handle_write_file,
    "edit_file": handle_edit_file,
    "bash": handle_bash,
    "schedule_task": handle_schedule_task,
}
