from contextlib import contextmanager

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models import Organization
from ..security import Principal, authorize


@contextmanager
def tenant_write(db: Session, principal: Principal, organization_id: str):
    """Authorize and serialize writes within one organization's transaction."""
    try:
        with db.begin():
            if db.get_bind().dialect.name == "sqlite":
                db.execute(text("BEGIN IMMEDIATE"))
            authorize(db, principal, organization_id, write=True)
            organization = db.scalar(
                select(Organization).where(Organization.id == organization_id).with_for_update()
            )
            if organization is None:
                raise HTTPException(404, "Business not found")
            authorize(db, principal, organization_id, write=True)
            yield
    except SQLAlchemyError:
        raise HTTPException(503, "Workspace write unavailable") from None
