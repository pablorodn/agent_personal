from app.config import Settings


def _settings(**overrides) -> Settings:
    base = {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "anon",
        "SUPABASE_SERVICE_ROLE_KEY": "service",
        "DATABASE_URL": "postgres://postgres:postgres@localhost:5432/postgres",
        "OPENROUTER_API_KEY": "test",
        "SECRET_KEY": "test-secret",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[call-arg]


def test_is_production_false_by_default():
    assert _settings().is_production is False


def test_is_production_false_for_non_production_values():
    assert _settings(ENVIRONMENT="development").is_production is False
    assert _settings(ENVIRONMENT="staging").is_production is False


def test_is_production_true_only_for_production():
    assert _settings(ENVIRONMENT="production").is_production is True
