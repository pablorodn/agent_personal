import asyncio

from app.config import get_settings

DENYLIST = ("rm -rf /", "mkfs", " dd ", ":(){ :|:& };:")


async def execute_bash(command: str, timeout_seconds: int = 30) -> dict:
    settings = get_settings()
    if not settings.is_bash_enabled:
        raise PermissionError("BASH_TOOL_ENABLED is not true")
    lowered = command.lower()
    if any(token in lowered for token in DENYLIST):
        raise PermissionError("Command blocked by policy")

    process = await asyncio.create_subprocess_exec(
        "bash",
        "-lc",
        command,
        cwd=str(settings.bash_cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except TimeoutError as exc:
        process.kill()
        raise TimeoutError("Bash command timed out") from exc
    return {"exit_code": process.returncode, "stdout": stdout.decode(), "stderr": stderr.decode()}
