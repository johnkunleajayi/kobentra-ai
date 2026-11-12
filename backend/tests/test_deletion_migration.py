from importlib import import_module
from io import StringIO

from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_deletion_postgresql_offline_ddl():
    migration = import_module("migrations.versions.2l002_business_deletions")
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    with Operations.context(context):
        migration.upgrade()
    ddl = output.getvalue()
    assert "CREATE TABLE business_deletions" in ddl
    assert "CREATE TABLE business_deletion_events" in ddl
    assert "deletion_state" in ddl and migration.down_revision == "2l001"
