"""Application Configuration."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Development-only default; refused when ENVIRONMENT is production (see production_problems)
INSECURE_DEV_SECRET = "dhan-insecure-development-secret-key-change-in-production-1234567890"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Project metadata
    PROJECT_NAME: str = "DHAN API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    # Off unless asked for: debug mode returns stack traces in error responses
    DEBUG: bool = False
    SECRET_KEY: str = INSECURE_DEV_SECRET

    # PostgreSQL Database Connection
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "dhan_user"
    POSTGRES_PASSWORD: str = "dhan_password"
    POSTGRES_DB: str = "dhan_db"

    DATABASE_URL: str = "postgresql+asyncpg://dhan_user:dhan_password@localhost:5432/dhan_db"
    SYNC_DATABASE_URL: str = "postgresql+psycopg://dhan_user:dhan_password@localhost:5432/dhan_db"
    DB_ECHO: bool = False

    # Authentication & Security
    JWT_SECRET_KEY: str = INSECURE_DEV_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Calendar used for "which day/month does this transaction fall in" when a request
    # doesn't name one (reports take ?tz=). DHAN users are in India.
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"

    # DHAN AI. "mock" answers from the user's own data with templates and costs nothing;
    # a paid model provider is only used if one is registered and named here explicitly.
    AI_PROVIDER: str = "mock"
    # Earlier turns of the conversation passed to the provider with each question
    AI_HISTORY_LIMIT: int = 10

    # Abuse protection: per-client request budgets for login, registration, token refresh
    # and AI questions (see core/rate_limit.py). In-memory, so per process.
    RATE_LIMIT_ENABLED: bool = True

    # Password reset codes are single use and expire after this long
    PASSWORD_RESET_TTL_MINUTES: int = 30

    # Server settings
    FASTAPI_HOST: str = "0.0.0.0"
    FASTAPI_PORT: int = 8000
    FASTAPI_CORS_ORIGINS: list[str] | str = ["*"]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def use_async_driver(cls, v: str) -> str:
        """Hosts such as Render hand out plain postgres:// URLs; the app talks to it via asyncpg."""
        for prefix in ("postgres://", "postgresql://"):
            if isinstance(v, str) and v.startswith(prefix):
                return "postgresql+asyncpg://" + v[len(prefix) :]
        return v

    @field_validator("FASTAPI_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() in ("production", "prod", "staging")

    def production_problems(self) -> list[str]:
        """Settings that are unsafe outside development; empty when the config is fit to deploy."""
        problems = []
        if self.DEBUG:
            problems.append("DEBUG must be false (debug responses expose stack traces)")
        for name in ("JWT_SECRET_KEY", "SECRET_KEY"):
            value = getattr(self, name)
            if value == INSECURE_DEV_SECRET or "insecure" in value.lower() or len(value) < 32:
                problems.append(f"{name} must be a unique random value of at least 32 characters")
        if self.JWT_ALGORITHM not in ("HS256", "HS384", "HS512"):
            problems.append("JWT_ALGORITHM must be an HMAC algorithm (HS256/384/512)")
        if "*" in self.FASTAPI_CORS_ORIGINS:
            problems.append("FASTAPI_CORS_ORIGINS must list the allowed origins, not '*'")
        if "dhan_password" in self.DATABASE_URL:
            problems.append("DATABASE_URL must not use the development database password")
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
