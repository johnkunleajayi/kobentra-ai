"""Request-scoped SQLAlchemy database sessions."""

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session


def get_db(request: Request) -> Generator[Session, None, None]:
    """Provide a database session from the application engine.

    The engine must be initialized during application startup.
    The dependency never commits implicitly.
    """

    engine = getattr(request.app.state, "database_engine", None)

    if engine is None:
        raise RuntimeError("Database engine is not initialized")

    with Session(engine) as session:
        yield session
