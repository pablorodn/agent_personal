from app.services.scheduler import compute_next_run_at


def test_compute_next_run_at_returns_iso():
    value = compute_next_run_at("*/5 * * * *", "UTC")
    assert "T" in value
