from sqlalchemy import select
from sqlalchemy.orm import Session

from .constants import ASSESSMENT_TYPE
from .models import BusinessAssessment


def pending(db: Session, business_id: str, survey_id: str, logical_id: str):
    return db.scalar(
        select(BusinessAssessment)
        .where(
            BusinessAssessment.organization_id == business_id,
            BusinessAssessment.assessment_type == ASSESSMENT_TYPE,
            BusinessAssessment.provider_survey_id == survey_id,
            BusinessAssessment.provider_logical_id == logical_id,
            BusinessAssessment.status.in_(["initiated", "launch_requested"]),
        )
        .order_by(BusinessAssessment.initiated_at, BusinessAssessment.id)
    )
