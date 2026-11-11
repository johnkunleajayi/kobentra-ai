from sqlalchemy.orm import Session

from ..models import Opportunity
from ..security import Principal, scoped_get, scoped_list
from ..workspace.transactions import tenant_write
from . import repository
from .schemas import OpportunityInput, OpportunityList, OpportunitySummary


def read_list(db: Session, principal: Principal, business_id: str):
    rows = scoped_list(db, Opportunity, principal, business_id)
    return OpportunityList(
        opportunities=[
            OpportunitySummary.model_validate(row) for row in sorted(rows, key=lambda r: r.id)
        ]
    )


def read_one(db: Session, principal: Principal, business_id: str, opportunity_id: str):
    return OpportunitySummary.model_validate(
        scoped_get(db, Opportunity, principal, business_id, opportunity_id)
    )


def create(db: Session, principal: Principal, business_id: str, data: OpportunityInput):
    with tenant_write(db, principal, business_id):
        row = repository.existing(db, business_id, data)
        created = row is None
        if created:
            row = repository.insert(db, business_id, data)
        result = OpportunitySummary.model_validate(row)
    return result, created


def update(
    db: Session, principal: Principal, business_id: str, opportunity_id: str, data: OpportunityInput
):
    with tenant_write(db, principal, business_id):
        row = scoped_get(db, Opportunity, principal, business_id, opportunity_id)
        row.title, row.stage = data.title, data.stage
        db.flush()
        result = OpportunitySummary.model_validate(row)
    return result
