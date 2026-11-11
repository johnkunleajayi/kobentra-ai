from fastapi import APIRouter, Depends, Request, Response

from ..business.routes import Database, Identity, require_write_origin
from ..workspace.identifiers import RecordID
from .dispatch import dispatch
from .schemas import AssessmentSummary, DispatchAssessment, InitiateAssessment
from .synchronize import synchronize

router = APIRouter(prefix="/api/businesses/{business_id}/assessments", tags=["Native assessments"])


def salesforce(request):
    # Token cache belongs to this application instance, never the browser.
    return request.app.state.salesforce_client


@router.post(
    "/{assessment_id}/dispatch",
    response_model=AssessmentSummary,
    dependencies=[Depends(require_write_origin)],
)
def send(
    business_id: RecordID,
    assessment_id: RecordID,
    data: DispatchAssessment,
    principal: Identity,
    db: Database,
    request: Request,
    response: Response,
):
    response.headers["Cache-Control"] = "no-store"
    return dispatch(
        db,
        principal,
        business_id,
        assessment_id,
        data,
        request.app.state.settings,
        salesforce(request),
    )


@router.post(
    "/{assessment_id}/sync",
    response_model=AssessmentSummary,
    dependencies=[Depends(require_write_origin)],
)
def sync(
    business_id: RecordID,
    assessment_id: RecordID,
    data: InitiateAssessment,
    principal: Identity,
    db: Database,
    request: Request,
    response: Response,
):
    response.headers["Cache-Control"] = "no-store"
    return synchronize(db, principal, business_id, assessment_id, salesforce(request))
