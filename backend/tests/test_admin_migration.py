import importlib
from io import StringIO

from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_postgresql_administrative_migration_offline():
    migration = importlib.import_module("migrations.versions.2l001_business_administration")
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    with Operations.context(context):
        migration.upgrade()
    ddl = output.getvalue()
    assert "CREATE TABLE business_administration" in ddl
    assert "CREATE TABLE administrative_decisions" in ddl
    assert "uq_admin_request" in ddl and "admin_approval" in ddl
    assert migration.down_revision == "2h001"
