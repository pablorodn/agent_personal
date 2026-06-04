from datetime import datetime
from zoneinfo import ZoneInfo

from croniter import croniter


def compute_next_run_at(cron_expr: str, timezone_name: str) -> str:
    base = datetime.now(ZoneInfo(timezone_name))
    nxt = croniter(cron_expr, base).get_next(datetime)
    return nxt.isoformat()
