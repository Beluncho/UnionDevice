from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process-only configuration. The application never opens an env file itself."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore", case_sensitive=False)

    app_env: str = "development"
    log_level: str = "INFO"
    llm_api_key: SecretStr | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str | None = None
    llm_http_proxy_url: SecretStr | None = None
    llm_timeout_seconds: float = Field(default=60.0, gt=0, le=300)
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    @field_validator("llm_base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("LLM_BASE_URL must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password:
            raise ValueError("Credentials are not allowed in LLM_BASE_URL")
        return value

    @field_validator("llm_api_key", "llm_http_proxy_url", "llm_model", mode="before")
    @classmethod
    def blank_optional_values(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

