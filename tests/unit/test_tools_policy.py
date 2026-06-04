from app.tools.catalog import get_tool_risk, tool_is_cron_safe, tool_requires_confirmation


def test_high_risk_tool_requires_confirmation():
    assert tool_requires_confirmation("bash") is True


def test_low_risk_tool_no_confirmation():
    assert tool_requires_confirmation("read_file") is False


def test_schedule_task_is_cron_safe():
    assert tool_is_cron_safe("schedule_task") is True


def test_unknown_tool_defaults_high_risk():
    assert get_tool_risk("unknown-tool") == "high"
