from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Opportunity
from .schemas import OpportunityInput


def existing(db: Session, business_id: str, data: OpportunityInput):
    return db.scalar(
        select(Opportunity)
        .where(
            Opportunity.organization_id == business_id,
            Opportunity.title == data.title,
            Opportunity.stage == data.stage,
        )
        .order_by(Opportunity.id)
    )


def insert(db: Session, business_id: str, data: OpportunityInput) -> Opportunity:
    row = Opportunity(organization_id=business_id, **data.model_dump())
    db.add(row)
    db.flush()
    return row
