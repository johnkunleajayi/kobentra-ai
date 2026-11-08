import certifi
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url

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

    engine = create_engine(
        url,
        echo=False,
        hide_parameters=True,
        pool_pre_ping=True,
    )

    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def enforce_foreign_keys(dbapi_connection, connection_record):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

    return engine


# Preserve the existing import contract for SQLite callers.
local_engine = database_engine
