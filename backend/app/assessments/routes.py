from fastapi import APIRouter, Depends, Request, Response

from ..business.routes import Database, Identity, require_write_origin
from ..security import authorize
from ..workspace.identifiers import RecordID
from . import service
from .provider import configuration
from .schemas import (
    AssessmentLaunch,
    AssessmentList,
    AssessmentSummary,
    InitiateAssessment,
    ProviderConfiguration,
)

router = APIRouter(prefix="/api/businesses/{business_id}/assessments", tags=["Assessments"])


@router.get("/config", response_model=ProviderConfiguration)
def provider_config(
    business_id: RecordID, principal: Identity, db: Database, request: Request, response: Response
):
    authorize(db, principal, business_id)
    response.headers["Cache-Control"] = "no-store"
    return configuration(request.app.state.settings)


@router.get("", response_model=AssessmentList)
def history(business_id: RecordID, principal: Identity, db: Database, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return service.list_assessments(db, principal, business_id)


@router.get("/{assessment_id}", response_model=AssessmentSummary)
def detail(
    business_id: RecordID,
    assessment_id: RecordID,
    principal: Identity,
    db: Database,
    response: Response,
):
    response.headers["Cache-Control"] = "no-store"
    return service.read_assessment(db, principal, business_id, assessment_id)


@router.post("", response_model=AssessmentSummary, dependencies=[Depends(require_write_origin)])
def initiate(
    business_id: RecordID,
    data: InitiateAssessment,
    principal: Identity,
    db: Database,
    request: Request,
    response: Response,
):
    result, created = service.initiate(db, principal, business_id, request.app.state.settings)
    response.status_code = 201 if created else 200
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post(
    "/{assessment_id}/launch",
    response_model=AssessmentLaunch,
    dependencies=[Depends(require_write_origin)],
)
def launch(
    business_id: RecordID,
    assessment_id: RecordID,
    data: InitiateAssessment,
    principal: Identity,
    db: Database,
    request: Request,
    response: Response,
):
    response.headers["Cache-Control"] = "no-store"
    return service.launch(db, principal, business_id, assessment_id, request.app.state.settings)
