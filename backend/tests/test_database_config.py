from io import StringIO
from pathlib import Path
from unittest.mock import Mock

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import event, text
from sqlalchemy.engine import make_url

from app.config import Settings
from app.database import database_engine

PG = "postgresql://sample:dummy%40password@neon-placeholder.invalid/sample"


@pytest.mark.parametrize("driver", ["postgresql", "postgresql+psycopg"])
def test_postgresql_engine_is_lazy_secure_and_has_no_sqlite_hook(driver, monkeypatch):
    connect = Mock(side_effect=AssertionError("No PostgreSQL connections permitted"))
    monkeypatch.setattr(psycopg, "connect", connect)
    register_hook = Mock(wraps=event.listens_for)
    monkeypatch.setattr(event, "listens_for", register_hook)
    settings = Settings(_env_file=None, database_url=PG.replace("postgresql", driver, 1))
    engine = database_engine(settings)
    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "psycopg"
    args, kwargs = engine.dialect.create_connect_args(engine.url)
    assert not args
    assert kwargs["sslmode"] == "verify-full"
    assert kwargs["channel_binding"] == "require"
    assert kwargs["password"] == "dummy@password"
    assert engine.echo is False and engine.hide_parameters is True
    register_hook.assert_not_called()
    connect.assert_not_called()
    engine.dispose()


def test_sqlite_foreign_keys_on_every_connection():
    engine = database_engine(Settings(_env_file=None, database_url="sqlite+pysqlite:///:memory:"))
    for _ in range(2):
        with engine.connect() as connection:
            assert connection.scalar(text("PRAGMA foreign_keys")) == 1
        engine.dispose()


@pytest.mark.parametrize(
    "suffix",
    [
        "?sslmode=disable",
        "?sslmode=require",
        "?sslmode=verify-ca",
        "?channel_binding=disable",
        "?host=other.invalid",
        "?sslmode=verify-full&sslmode=require",
    ],
)
def test_insecure_or_ambiguous_postgresql_options_rejected(suffix):
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None, database_url=PG + suffix)
    assert "dummy" not in str(exc.value)
    assert "neon-placeholder" not in str(exc.value)


@pytest.mark.parametrize(
    "url",
    [
        "garbage",
        "mysql://sample:dummy@host/db",
        "postgresql://host/db",
        "sqlite+pysqlite://host/db",
    ],
)
def test_invalid_urls_are_rejected_without_echoing_input(url):
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None, database_url=url)
    assert url not in str(exc.value)


def test_secret_redaction_and_encoded_credentials():
    settings = Settings(_env_file=None, database_url=PG)
    assert "dummy" not in repr(settings)
    assert "dummy" not in settings.model_dump_json()
    assert make_url(settings.database_url.get_secret_value()).password == "dummy@password"


def test_dotenv_loading_and_environment_precedence(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    dotenv = tmp_path / ".env"
    dotenv.write_text("DATABASE_URL=" + PG + "\n")
    assert (
        make_url(Settings(_env_file=dotenv).database_url.get_secret_value()).drivername
        == "postgresql+psycopg"
    )
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    assert (
        make_url(Settings(_env_file=dotenv).database_url.get_secret_value()).get_backend_name()
        == "sqlite"
    )
    assert Path(Settings.model_config["env_file"]).name == ".env"
    assert Path(Settings.model_config["env_file"]).parent.name == "backend"


@pytest.mark.parametrize("url", ["sqlite+pysqlite:///:memory:", PG])
def test_complete_migration_sql_generates_offline(url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(psycopg, "connect", Mock(side_effect=AssertionError("Offline only")))
    output = StringIO()
    config = Config("alembic.ini", output_buffer=output)
    command.upgrade(config, "head", sql=True)
    command.downgrade(config, "head:base", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE introduction_requests" in sql
    assert "FOREIGN KEY(opportunity_id, organization_id)" in sql
    assert "DROP TABLE introduction_requests" in sql
    assert "dummy" not in sql and "neon-placeholder" not in sql
    if url == PG:
        assert "TIMESTAMP WITH TIME ZONE" in sql
        assert "PRAGMA" not in sql
    psycopg.connect.assert_not_called()
