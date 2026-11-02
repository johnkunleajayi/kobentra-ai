from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="forbid")
    app_env: Literal["development", "test"] = "development"
    database_url: str = "sqlite+pysqlite:///./kobentra-local.db"
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]

    @field_validator("database_url")
    @classmethod
    def local_database_only(cls, value: str) -> str:
        if not value.startswith("sqlite+pysqlite:///"):
            raise ValueError(
                "Phase 1 permits local SQLite only; remote provisioning needs approval"
            )
        return value

    @field_validator("cors_origins")
    @classmethod
    def explicit_origins(cls, values: list[str]) -> list[str]:
        from urllib.parse import urlparse

        if not values or any(
            v == "*"
            or urlparse(v).scheme not in {"http", "https"}
            or not urlparse(v).netloc
            or urlparse(v).path
            or urlparse(v).query
            or urlparse(v).fragment
            or urlparse(v).username
            for v in values
        ):
            raise ValueError(
                "CORS requires explicit HTTP origins without paths, wildcards or credentials"
            )
        return values
