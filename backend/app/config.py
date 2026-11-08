from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        extra="forbid",
        hide_input_in_errors=True,
    )
    app_env: Literal["development", "test"] = "development"
    database_url: SecretStr = SecretStr("sqlite+pysqlite:///./kobentra-local.db")
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]

    # Google OpenID Connect
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    google_redirect_uri: str = "http://127.0.0.1:8002/api/auth/google/callback"

    # Secret used to sign temporary OAuth transaction cookies.
    # The actual user sessions are stored in PostgreSQL.
    oauth_session_secret: SecretStr | None = None
    # Application session configuration
    session_cookie_name: str = "kobentra_session"
    session_lifetime_hours: int = 24
    frontend_url: str = "http://127.0.0.1:5173"

    @field_validator("database_url")
    @classmethod
    def supported_database(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
            if url.drivername == "sqlite+pysqlite":
                if url.host or url.username or url.password or not url.database or url.query:
                    raise ValueError
            elif url.drivername in {"postgresql", "postgresql+psycopg"}:
                if not all((url.host, url.username, url.password, url.database)):
                    raise ValueError
                query = dict(url.query)
                if set(query) - {"sslmode", "channel_binding", "sslrootcert", "connect_timeout"}:
                    raise ValueError
                query.setdefault("sslmode", "verify-full")
                query.setdefault("channel_binding", "require")
                if query["sslmode"] != "verify-full" or query["channel_binding"] != "require":
                    raise ValueError
                if any(not isinstance(v, str) or not v for v in query.values()):
                    raise ValueError
                url = url.set(drivername="postgresql+psycopg", query=query)
            else:
                raise ValueError
            return SecretStr(url.render_as_string(hide_password=False))
        except (ArgumentError, ValueError, TypeError):
            raise ValueError(
                "Invalid database configuration: use local sqlite+pysqlite or PostgreSQL "
                "with credentials, sslmode=verify-full and channel_binding=require"
            ) from None

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


