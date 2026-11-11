from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.config import Settings
from app.database import database_engine


def test_migration_preserves_legacy_assessments(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "sqlite+pysqlite:///" + (tmp_path / "migration.db").as_posix()
    )
    config = Config("alembic.ini")
    command.upgrade(config, "2f001")
    engine = database_engine(Settings())
    with engine.begin() as db:
        db.execute(
            text("INSERT INTO users (id,email) VALUES ('sample-user','sample@example.invalid')")
        )
        db.execute(text("INSERT INTO organizations (id,name) VALUES ('sample-org','Sample')"))
        db.execute(
            text(
                "INSERT INTO business_profiles (id,organization_id,name,sector,country,goal) VALUES ('sample-profile','sample-org','Sample','Trade','Ghana','Buy')"
            )
        )
        db.execute(
            text(
                "INSERT INTO business_assessments (id,organization_id,business_id,provider,assessment_type,provider_survey_id,provider_logical_id,status,initiated_by,initiated_at,integration_mode) VALUES ('legacy','sample-org','sample-org','surveyvista','partner_qualification','sample','sample','initiated','sample-user',CURRENT_TIMESTAMP,'shared_public_link')"
            )
        )
    engine.dispose()
    command.upgrade(config, "head")
    command.check(config)
    engine = database_engine(Settings())
    with engine.connect() as db:
        row = db.execute(
            text(
                "SELECT integration_mode,salesforce_lead_id,dispatch_state FROM business_assessments WHERE id='legacy'"
            )
        ).one()
        assert tuple(row) == ("shared_public_link", None, None)
    engine.dispose()
    command.downgrade(config, "2f001")
