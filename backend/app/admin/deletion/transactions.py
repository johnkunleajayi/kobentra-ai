from contextlib import contextmanager

from fastapi import HTTPException
from sqlalchemy import select, text

from ...models import Organization, User
from ..authorization import is_platform_owner


@contextmanager
def owner_transaction(db, principal, settings, business_id):
    db.rollback()  # End dependency read; every write rechecks authority under the organization lock.
    with db.begin():
        if db.get_bind().dialect.name == "sqlite":
            db.execute(text("BEGIN IMMEDIATE"))
        org = db.scalar(
            select(Organization).where(Organization.id == business_id).with_for_update()
        )
        if not is_platform_owner(db.get(User, principal.user_id), settings):
            raise HTTPException(403, "Access denied")
        if org is None:
            raise HTTPException(404, "Business not found")
        yield org
