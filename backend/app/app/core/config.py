# -*- coding: utf-8 -*-
# pylint: disable=no-member
import os
import secrets
from typing import Any, Optional

# fmt: off
from pydantic import AnyHttpUrl, PostgresDsn, field_validator, ValidationInfo
# fmt: on
from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseModel):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file="./.env" if os.path.isfile("./.env") else os.path.expanduser("~/.env"),
        validate_default=True,
        extra='allow'
    )
    """Settings for the app."""

    API_VERSION: str = "v1"
    API_V1_STR: str = f"/api/{API_VERSION}"
    PROJECT_NAME: str = "test"
    ENABLE_LLM_CACHE: bool = False
    # OpenAI Configuration
    OPENAI_API_KEY: str = "test-key"
    OPENAI_ORGANIZATION: Optional[str] = None
    OPENAI_API_BASE: Optional[str] = None

    # Anthropic Configuration
    ANTHROPIC_API_KEY: str = "test-key"
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com"

    # Google AI Configuration
    GOOGLE_API_KEY: str = "test-key"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"
    DATABASE_HOST: str = "database"
    DATABASE_PORT: int | str = 5432
    DATABASE_NAME: str = "fastapi_db"
    DATABASE_CELERY_NAME: str = "celery_schedule_jobs"
    REDIS_HOST: str = "redis_server"
    REDIS_PORT: int = 6379
    DB_POOL_SIZE: int = 83
    WEB_CONCURRENCY: int = 9
    POOL_SIZE: int = max(
        DB_POOL_SIZE // WEB_CONCURRENCY,
        5,
    )
    ASYNC_DATABASE_URI: Optional[str] = None

    @field_validator("ASYNC_DATABASE_URI", mode="before")
    def assemble_db_connection(
        cls,
        v: str | None,
        info: ValidationInfo,
    ) -> Any:
        if isinstance(v, str):
            return v
        try:
            return PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=info.data.get("DATABASE_USER", "postgres"),
                password=info.data.get("DATABASE_PASSWORD", "postgres"),
                host=f"{info.data.get('DATABASE_HOST', 'database')}:{info.data.get('DATABASE_PORT', '5432')}",
                path=f"{info.data.get('DATABASE_NAME', 'fastapi_db')}",
            ).unicode_string()
        except Exception:
            # During testing, return a dummy URI if environment variables are not set
            if os.getenv("TESTING", "false").lower() == "true":
                return "postgresql+asyncpg://postgres:postgres@database:5432/fastapi_db"
            raise

    SYNC_CELERY_DATABASE_URI: Optional[str] = None

    @field_validator("SYNC_CELERY_DATABASE_URI", mode="before")
    def assemble_celery_db_connection(
        cls,
        v: str | None,
        info: ValidationInfo,
    ) -> Any:
        if isinstance(v, str):
            return v
        try:
            return PostgresDsn.build(
                scheme="postgresql",
                username=info.data.get("DATABASE_USER", "postgres"),
                password=info.data.get("DATABASE_PASSWORD", "postgres"),
                host=f"{info.data.get('DATABASE_HOST', 'database')}:{info.data.get('DATABASE_PORT', '5432')}",
                path=f"{info.data.get('DATABASE_CELERY_NAME', '')}",
            ).unicode_string()
        except Exception:
            if os.getenv("TESTING", "false").lower() == "true":
                return "postgresql://postgres:postgres@database:5432/celery_schedule_jobs"
            raise

    SYNC_CELERY_BEAT_DATABASE_URI: Optional[str] = None

    @field_validator("SYNC_CELERY_BEAT_DATABASE_URI", mode="before")
    def assemble_celery_beat_db_connection(
        cls,
        v: str | None,
        info: ValidationInfo,
    ) -> Any:
        if isinstance(v, str):
            return v
        try:
            return PostgresDsn.build(
                scheme="postgresql",
                username=info.data.get("DATABASE_USER", "postgres"),
                password=info.data.get("DATABASE_PASSWORD", "postgres"),
                host=f"{info.data.get('DATABASE_HOST', 'database')}:{info.data.get('DATABASE_PORT', '5432')}",
                path=f"{info.data.get('DATABASE_CELERY_NAME', '')}",
            ).unicode_string()
        except Exception:
            if os.getenv("TESTING", "false").lower() == "true":
                return "postgresql://postgres:postgres@database:5432/celery_schedule_jobs"
            raise

    ASYNC_CELERY_BEAT_DATABASE_URI: Optional[str] = None

    @field_validator("ASYNC_CELERY_BEAT_DATABASE_URI", mode="before")
    def assemble_async_celery_beat_db_connection(
        cls,
        v: str | None,
        info: ValidationInfo,
    ) -> Any:
        if isinstance(v, str):
            return v
        try:
            return PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=info.data.get("DATABASE_USER", "postgres"),
                password=info.data.get("DATABASE_PASSWORD", "postgres"),
                host=f"{info.data.get('DATABASE_HOST', 'database')}:{info.data.get('DATABASE_PORT', '5432')}",
                path=f"{info.data.get('DATABASE_CELERY_NAME', '')}",
            ).unicode_string()
        except Exception:
            if os.getenv("TESTING", "false").lower() == "true":
                return "postgresql+asyncpg://postgres:postgres@database:5432/celery_schedule_jobs"
            raise

    MINIO_ROOT_USER: str = "test"
    MINIO_ROOT_PASSWORD: str = "test"
    MINIO_URL: str = "test"
    MINIO_BUCKET: str = "test"

    ENABLE_AUTH: bool = False
    NEXTAUTH_SECRET: Optional[str] = None

    SECRET_KEY: str = secrets.token_urlsafe(32)
    BACKEND_CORS_ORIGINS: list[str] | list[AnyHttpUrl] = ["http://localhost"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(
        cls,
        v: str | list[str],
    ) -> list[str] | str:
        """Assemble CORS origins."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        if isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    PDF_TOOL_EXTRACTION_CONFIG_PATH: str = "test"
    AGENT_CONFIG_PATH: str = "tests/config/agent-test.yml"

    ################################
    # Tool specific configuration
    ################################
    SQL_TOOL_DB_ENABLED: bool = False
    SQL_TOOL_DB_SCHEMAS: list[str] = []
    SQL_TOOL_DB_INFO_PATH: str = "test"
    SQL_TOOL_DB_URI: str = ""
    SQL_TOOL_DB_OVERWRITE_ON_START: bool = True

    @field_validator("SQL_TOOL_DB_URI", mode="before")
    def assemble_sql_tool_db_connection(
        cls,
        v: str | None,
        info: ValidationInfo,
    ) -> Any:
        if not info.data.get("SQL_TOOL_DB_ENABLED"):
            return ""
        if isinstance(v, str):
            return make_url(v).render_as_string(hide_password=False)
        raise ValueError(v)

    PDF_TOOL_ENABLED: bool = True
    PDF_TOOL_LOG_QUERY: bool = False
    PDF_TOOL_LOG_QUERY_PATH: str = "app/tool_constants/query_log"
    PDF_TOOL_DATA_PATH: str = "test"
    PDF_TOOL_DATABASE: str = "test"

    ################################
    # BigQuery Tool Configuration
    ################################
    BIGQUERY_ENABLED: bool = False
    BIGQUERY_PROJECT_ID: Optional[str] = None
    BIGQUERY_DATASET: Optional[str] = None
    BIGQUERY_CREDENTIALS_PATH: Optional[str] = None
    BIGQUERY_MAX_BYTES_PROCESSED: int = 1_000_000_000  # 1GB default limit
    BIGQUERY_POOL_SIZE: int = 10

    @field_validator("BIGQUERY_CREDENTIALS_PATH")
    def validate_credentials_path(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Validate that credentials file exists if BigQuery is enabled."""
        if info.data.get("BIGQUERY_ENABLED", False):
            if not v:
                raise ValueError("BIGQUERY_CREDENTIALS_PATH is required when BigQuery is enabled")
            if not os.path.isfile(v):
                raise ValueError(f"BigQuery credentials file not found at: {v}")
        return v

settings = Settings()  # type: ignore
yaml_configs: dict[str, Any] = {}
