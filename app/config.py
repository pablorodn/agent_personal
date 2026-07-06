from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_anon_key: str = Field(alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(alias="SUPABASE_SERVICE_ROLE_KEY")
    database_url: str = Field(alias="DATABASE_URL")
    openrouter_api_key: str = Field(alias="OPENROUTER_API_KEY")
    secret_key: str = Field(alias="SECRET_KEY")

    file_tools_enabled: str | None = Field(default=None, alias="FILE_TOOLS_ENABLED")
    file_tools_root: str | None = Field(default=None, alias="FILE_TOOLS_ROOT")

    langfuse_public_key: str | None = Field(default=None, alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str | None = Field(default=None, alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="https://cloud.langfuse.com", alias="LANGFUSE_HOST")

    mcp_example_server_url: str | None = Field(default=None, alias="MCP_EXAMPLE_SERVER_URL")

    environment: str = Field(default="development", alias="ENVIRONMENT")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_file_tools_enabled(self) -> bool:
        return self.file_tools_enabled == "true"

    @property
    def file_tools_allowed_root(self) -> Path:
        return Path(self.file_tools_root or Path.cwd()).resolve()

    @property
    def normalized_database_url(self) -> str:
        return self.database_url.strip().strip("'").strip('"')

    @property
    def database_host(self) -> str | None:
        parsed = urlparse(self.normalized_database_url)
        return parsed.hostname


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
