from fastapi import APIRouter, Depends, Response

from ..business.routes import Database, Identity, require_write_origin
from ..workspace.identifiers import RecordID
from . import service
from .schemas import OpportunityInput, OpportunityList, OpportunitySummary

router = APIRouter(prefix="/api/businesses/{business_id}/opportunities", tags=["Opportunities"])


@router.get("", response_model=OpportunityList)
def list_opportunities(
    business_id: RecordID, principal: Identity, db: Database, response: Response
):
    response.headers["Cache-Control"] = "no-store"
    return service.read_list(db, principal, business_id)


@router.get("/{opportunity_id}", response_model=OpportunitySummary)
def get_opportunity(
    business_id: RecordID,
    opportunity_id: RecordID,
    principal: Identity,
    db: Database,
    response: Response,
):
    response.headers["Cache-Control"] = "no-store"
    return service.read_one(db, principal, business_id, opportunity_id)


@router.post("", response_model=OpportunitySummary, dependencies=[Depends(require_write_origin)])
def create_opportunity(
    business_id: RecordID,
    data: OpportunityInput,
    principal: Identity,
    db: Database,
    response: Response,
):
    result, created = service.create(db, principal, business_id, data)
    response.status_code = 201 if created else 200
    response.headers["Cache-Control"] = "no-store"
    return result


@router.put(
    "/{opportunity_id}",
    response_model=OpportunitySummary,
    dependencies=[Depends(require_write_origin)],
)
def update_opportunity(
    business_id: RecordID,
    opportunity_id: RecordID,
    data: OpportunityInput,
    principal: Identity,
    db: Database,
    response: Response,
):
    response.headers["Cache-Control"] = "no-store"
    return service.update(db, principal, business_id, opportunity_id, data)
