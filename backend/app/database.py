import certifi
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.pool import NullPool

from .config import Settings


def database_engine(settings: Settings) -> Engine:
    # Engine creation is lazy; no database connection occurs here.
    url = make_url(settings.database_url.get_secret_value())

    if url.get_backend_name() == "postgresql":
        # Use a trusted CA bundle while preserving hostname verification.
        url = url.update_query_dict(
            {
                "sslmode": "verify-full",
                "channel_binding": "require",
                "sslrootcert": certifi.where(),
            }
        )

    options = {}
    if settings.app_env == "production":
        # Neon supplies transaction pooling; do not retain pools per serverless instance.
        options = {
            "poolclass": NullPool,
            "connect_args": {
                "connect_timeout": 10,
                "prepare_threshold": None,
            },
        }
    engine = create_engine(
        url,
        echo=False,
        hide_parameters=True,
        pool_pre_ping=True,
        **options,
    )

    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def enforce_foreign_keys(dbapi_connection, connection_record):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

    elif settings.app_env == "production":

        @event.listens_for(engine, "begin")
        def bound_database_waits(connection):
            # Transaction-local settings work with transaction poolers and never leak.
            connection.exec_driver_sql("SET LOCAL statement_timeout = '20s'")
            connection.exec_driver_sql("SET LOCAL lock_timeout = '5s'")

    return engine


# Preserve the existing import contract for SQLite callers.
local_engine = database_engine
