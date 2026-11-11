from fastapi import HTTPException
from sqlalchemy import select

from ..assessments.models import BusinessAssessment
from ..models import BusinessProfile, MarketPreference
from ..qualification.models import AssessmentEvidence
from ..qualification.provider import MAPPING
from ..qualification.scoring import evaluate
from .eligibility import status
from .repository import owners, profile_summary


def business_detail(db, business_id):
    profile = db.scalar(
        select(BusinessProfile).where(BusinessProfile.organization_id == business_id)
    )
    if profile is None:
        raise HTTPException(404, "Business not found")
    preferences = list(
        db.scalars(select(MarketPreference).where(MarketPreference.organization_id == business_id))
    )
    evidence = list(
        db.scalars(
            select(AssessmentEvidence)
            .join(
                BusinessAssessment,
                (BusinessAssessment.id == AssessmentEvidence.assessment_id)
                & (BusinessAssessment.organization_id == AssessmentEvidence.organization_id),
            )
            .where(
                AssessmentEvidence.organization_id == business_id,
                BusinessAssessment.status == "completed_verified",
                BusinessAssessment.integration_mode == "salesforce_flow",
                BusinessAssessment.provider_survey_id == MAPPING["survey_id"],
                BusinessAssessment.provider_response_id == AssessmentEvidence.provider_response_id,
            )
        )
    )
    qualification = evaluate(evidence, profile, preferences)
    state = status(db, business_id)
    if state["identity"] == "verified":
        qualification["qualification_gaps"] = [
            g for g in qualification["qualification_gaps"] if g["code"] != "business_identity"
        ]
    # Summary only: no raw/normalized answers, provider IDs, recipient contacts or dispatch payload.
    assessments = list(
        db.scalars(
            select(BusinessAssessment)
            .where(BusinessAssessment.organization_id == business_id)
            .order_by(BusinessAssessment.initiated_at.desc(), BusinessAssessment.id)
            .limit(100)
        )
    )
    return {
        **profile_summary(profile, owners(db, [business_id])[business_id]),
        "administration": state,
        "profile": {key: getattr(profile, key) for key in ("name", "sector", "country", "goal")},
        "assessment_history_limit": 100,
        "assessments": [
            {
                "id": a.id,
                "status": a.status,
                "initiated_at": a.initiated_at,
                "completed_at": a.completed_at,
                "provider": a.provider,
            }
            for a in assessments
        ],
        "qualification": {
            "readiness": qualification["readiness"],
            "confidence": qualification["confidence"],
            "completeness": qualification["completeness"],
            "gaps": qualification["qualification_gaps"],
        },
    }
