from sqlalchemy import create_engine, event

from .config import Settings


def local_engine(settings: Settings):
    engine = create_engine(settings.database_url)

    @event.listens_for(engine, "connect")
    def enforce_foreign_keys(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    return engine
