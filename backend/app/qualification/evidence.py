"""Shared, tenant-bound selection of immutable verified native evidence."""

from sqlalchemy import select

from ..assessments.models import BusinessAssessment
from .models import AssessmentEvidence
from .provider import MAPPING


def eligible_query(ids):
    return (
        select(AssessmentEvidence)
        .join(
            BusinessAssessment,
            (BusinessAssessment.id == AssessmentEvidence.assessment_id)
            & (BusinessAssessment.organization_id == AssessmentEvidence.organization_id),
        )
        .where(
            AssessmentEvidence.organization_id.in_(ids),
            BusinessAssessment.status == "completed_verified",
            BusinessAssessment.integration_mode == "salesforce_flow",
            BusinessAssessment.provider_survey_id == MAPPING["survey_id"],
            BusinessAssessment.provider_response_id == AssessmentEvidence.provider_response_id,
            AssessmentEvidence.extraction_version == MAPPING["extraction_version"],
        )
    )


def eligible(db, business_id):
    return list(db.scalars(eligible_query([business_id]).order_by(AssessmentEvidence.id)))
