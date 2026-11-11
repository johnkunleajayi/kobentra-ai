from fastapi import APIRouter, Depends, Request, Response

from ..assessments.native_routes import salesforce
from ..assessments.schemas import InitiateAssessment
from ..business.routes import Database, Identity, require_write_origin
from ..workspace.identifiers import RecordID
from .policy import foundation
from .service import ingest, snapshot

router = APIRouter(prefix="/api/businesses/{business_id}", tags=["Qualification evidence"])


@router.post("/assessments/{assessment_id}/ingest", dependencies=[Depends(require_write_origin)])
def ingest_response(
    business_id: RecordID,
    assessment_id: RecordID,
    data: InitiateAssessment,
    principal: Identity,
    db: Database,
    request: Request,
    response: Response,
):
    result, created = ingest(db, principal, business_id, assessment_id, salesforce(request))
    response.status_code = 201 if created else 200
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get("/assessments/{assessment_id}/evidence")
def read_evidence(
    business_id: RecordID,
    assessment_id: RecordID,
    principal: Identity,
    db: Database,
    response: Response,
):
    response.headers["Cache-Control"] = "no-store"
    return snapshot(db, principal, business_id, assessment_id)


@router.get("/qualification")
def qualification(business_id: RecordID, principal: Identity, db: Database, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return foundation(db, principal, business_id)
