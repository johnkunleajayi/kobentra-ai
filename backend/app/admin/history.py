from fastapi import HTTPException
from sqlalchemy import func, select

from ..models import Organization
from .models import AdministrativeDecision


def history(db, business_id, page):
    if db.get(Organization, business_id) is None:
        raise HTTPException(404, "Business not found")
    query = select(AdministrativeDecision).where(
        AdministrativeDecision.organization_id == business_id
    )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(
        query.order_by(AdministrativeDecision.created_at.desc(), AdministrativeDecision.id)
        .offset((page - 1) * 20)
        .limit(20)
    )
    return {
        "total": total,
        "page": page,
        "page_size": 20,
        "items": [
            {
                key: getattr(row, key)
                for key in (
                    "id",
                    "actor_id",
                    "action",
                    "reason",
                    "evidence_references",
                    "previous_values",
                    "new_values",
                    "created_at",
                )
            }
            for row in rows
        ],
    }
