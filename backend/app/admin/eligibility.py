from fastapi import HTTPException
from sqlalchemy import select

from .models import BusinessAdministration


def status(db, business_id):
    row = db.scalar(
        select(BusinessAdministration)
        .where(BusinessAdministration.organization_id == business_id)
        .execution_options(populate_existing=True)
    )
    return (
        values(row)
        if row
        else dict(approval="pending", identity="unverified", access="active", version=0)
    )


def values(row):
    return {key: getattr(row, key) for key in ("approval", "identity", "access", "version")}


def require_operational(db, business_id):
    if status(db, business_id)["access"] == "suspended":
        raise HTTPException(403, "Business access suspended")


def discoverable(state):
    return state["approval"] == "approved" and state["access"] == "active"


def statuses(db, ids):
    return {
        row.organization_id: values(row)
        for row in db.scalars(
            select(BusinessAdministration).where(BusinessAdministration.organization_id.in_(ids))
        )
    }
