from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.config import Settings
from app.database import local_engine


def test_migration_upgrade_downgrade_roundtrip(tmp_path, monkeypatch):
    path = tmp_path / "roundtrip.db"
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///" + path.as_posix())
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = local_engine(Settings())
    assert "introduction_requests" in inspect(engine).get_table_names()
    engine.dispose()
    command.check(config)
    command.downgrade(config, "base")
    engine = local_engine(Settings())
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()
    command.upgrade(config, "head")
