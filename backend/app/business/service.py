from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from . import repository
from .schemas import BusinessRegistration, BusinessSummary


def register_business(
    db: Session, user_id: str, data: BusinessRegistration
) -> tuple[BusinessSummary, bool]:
    """Serialize registrations by creator and commit all records together.

    Exact normalized retries return the existing owned profile. Distinct profiles
    remain permitted. PostgreSQL's default READ COMMITTED sees the preceding
    registration after acquiring the creator row lock. SQLite uses a write lock.
    """
    try:
        with db.begin():
            if db.bind.dialect.name == "sqlite":
                db.execute(text("BEGIN IMMEDIATE"))
            if repository.lock_registrant(db, user_id) is None:
                raise HTTPException(401, "Authentication required")
            profile = repository.existing_registration(db, user_id, data)
            created = profile is None
            if created:
                profile = repository.create_business(db, user_id, data)
            from ..admin.eligibility import require_operational
            require_operational(db, profile.organization_id)
            result = repository.summarize(profile, "owner")
        return result, created
    except SQLAlchemyError:
        # The transaction context rolls back every insert, including commit failures.
        raise HTTPException(503, "Business registration unavailable") from None
