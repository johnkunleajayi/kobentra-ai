from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..config import Settings
from ..security import Principal, scoped_get, scoped_list
from ..workspace.transactions import tenant_write
from .constants import ASSESSMENT_TYPE
from .dispatch import SURVEY_ID
from .models import BusinessAssessment
from .provider import configured_survey
from .repository import pending
from .schemas import AssessmentLaunch, AssessmentList, AssessmentSummary


def list_assessments(db: Session, principal: Principal, business_id: str):
    rows = scoped_list(db, BusinessAssessment, principal, business_id)
    return AssessmentList(
        assessments=[
            AssessmentSummary.model_validate(row)
            for row in sorted(rows, key=lambda r: (r.initiated_at, r.id), reverse=True)
        ]
    )


def read_assessment(db: Session, principal: Principal, business_id: str, assessment_id: str):
    return AssessmentSummary.model_validate(
        scoped_get(db, BusinessAssessment, principal, business_id, assessment_id)
    )


def initiate(db: Session, principal: Principal, business_id: str, settings: Settings):
    with tenant_write(db, principal, business_id):
        if settings.salesforce_dispatch_enabled:
            survey, logical = SURVEY_ID, "salesforce_flow"
        else:
            _, survey, logical = configured_survey(settings)
        record = pending(db, business_id, survey, logical)
        created = record is None
        if created:
            record = BusinessAssessment(
                organization_id=business_id,
                business_id=business_id,
                assessment_type=ASSESSMENT_TYPE,
                provider_survey_id=survey,
                provider_logical_id=logical,
                initiated_by=principal.user_id,
                integration_mode="salesforce_flow"
                if settings.salesforce_dispatch_enabled
                else "shared_public_link",
            )
            db.add(record)
            db.flush()
        result = AssessmentSummary.model_validate(record)
    return result, created


def launch(
    db: Session, principal: Principal, business_id: str, assessment_id: str, settings: Settings
):
    with tenant_write(db, principal, business_id):
        record = scoped_get(db, BusinessAssessment, principal, business_id, assessment_id)
        if settings.salesforce_dispatch_enabled or record.integration_mode == "salesforce_flow":
            raise HTTPException(
                409, "Native invitations are dispatched by email, not a public link"
            )
        if record.status not in {"initiated", "launch_requested"}:
            raise HTTPException(409, "A verified assessment cannot be relaunched")
        url, survey, logical = configured_survey(settings)
        if (survey, logical) != (record.provider_survey_id, record.provider_logical_id):
            raise HTTPException(409, "The configured survey has changed")
        if record.status == "initiated":
            record.status = "launch_requested"
        db.flush()
        result = AssessmentLaunch(
            assessment=AssessmentSummary.model_validate(record), launch_url=url
        )
    return result
