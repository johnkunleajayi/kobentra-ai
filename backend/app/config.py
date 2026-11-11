from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from .assessments.constants import PUBLIC_URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        extra="forbid",
        hide_input_in_errors=True,
    )
    app_env: Literal["development", "test"] = "development"
    platform_owner_google_subject: SecretStr | None = None

    @field_validator("platform_owner_google_subject")
    @classmethod
    def owner_subject(cls, value):
        if value is not None and (not value.get_secret_value().strip() or len(value.get_secret_value()) > 255):
            raise ValueError("Invalid platform-owner configuration")
        return value
    # Explicit publication approval covers name/sector/country and derived market-interest compatibility.
    # Empty by default: registration alone does not consent to cross-tenant discovery.
    matching_discovery_business_ids: list[str] = []

    @field_validator("matching_discovery_business_ids")
    @classmethod
    def explicit_discovery_ids(cls, values):
        from uuid import UUID

        if len(values) > 200:
            raise ValueError("Discovery directory exceeds local limit")
        return sorted({str(UUID(value)) for value in values})
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
    surveyvista_launch_url: str | None = PUBLIC_URL
    salesforce_instance_url: str | None = None
    salesforce_client_id: SecretStr | None = None
    salesforce_client_secret: SecretStr | None = None
    salesforce_dispatch_enabled: bool = False
    salesforce_result_survey_field: str | None = None
    salesforce_result_status_field: str | None = None

    @field_validator("salesforce_result_survey_field", "salesforce_result_status_field")
    @classmethod
    def salesforce_field_name(cls, value):
        import re

        if value is not None and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value):
            raise ValueError("Invalid Salesforce field API name")
        return value

    @field_validator("salesforce_instance_url")
    @classmethod
    def salesforce_origin(cls, value):
        from urllib.parse import urlparse

        if value is None:
            return None
        parsed = urlparse(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or not parsed.hostname.endswith(".my.salesforce.com")
            or parsed.netloc != parsed.hostname
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Salesforce requires an HTTPS My Domain origin")
        return value.rstrip("/")

    @field_validator("surveyvista_launch_url")
    @classmethod
    def survey_launch_url(cls, value: str | None) -> str | None:
        from urllib.parse import parse_qs, urlparse

        if not value:
            return None
        url = urlparse(value)
        query = parse_qs(url.query, keep_blank_values=True)
        if (
            url.scheme != "https"
            or url.hostname != "orgfarm-7cee962a58-dev-ed.develop.my.site.com"
            or url.netloc != url.hostname
            or url.path != "/kobentraassess/s/survey-response"
            or url.fragment
            or set(query) != {"recordId", "logicalId"}
            or any(len(v) != 1 or not v[0] or len(v[0]) > 100 for v in query.values())
        ):
            raise ValueError("Invalid SurveyVista public launch URL")
        return value

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
