from fastapi import HTTPException
from sqlalchemy import select

from ..admin.eligibility import status
from ..assessments.models import BusinessAssessment
from ..models import BusinessProfile, MarketPreference
from ..security import authorize
from .models import AssessmentEvidence
from .provider import MAPPING
from .scoring import evaluate

MANDATORY_VERIFICATIONS = ("business_identity",)


def introduction_policy(required, independently_verified):
    missing = sorted(set(required) - set(independently_verified))
    return {
        "discovery_eligible": True,
        "introduction_allowed": not missing,
        "missing_verifications": missing,
    }


def require_introduction_evidence(db, principal, business_id):
    """Future real introduction endpoints must call this server-side gate.

    Owner identity decisions are independent of survey self-reporting. Even a
    verified identity cannot bypass the unimplemented mutual-consent workflow.
    """
    authorize(db, principal, business_id, write=True)
    if status(db, business_id)["identity"] != "verified":
        raise HTTPException(409, "Mandatory independent verification is missing")
    raise HTTPException(409, "Mutual introduction consent workflow is not implemented")


def foundation(db, principal, business_id):
    authorize(db, principal, business_id)
    administration = status(db, business_id)
    profile = db.scalar(
        select(BusinessProfile).where(BusinessProfile.organization_id == business_id)
    )
    prefs = list(
        db.scalars(select(MarketPreference).where(MarketPreference.organization_id == business_id))
    )
    evidence = list(
        db.scalars(
            select(AssessmentEvidence).where(AssessmentEvidence.organization_id == business_id)
        )
    )
    gaps = sorted({gap for row in evidence for gap in row.gaps} | set(MANDATORY_VERIFICATIONS))
    if not evidence:
        gaps.append("assessment_answers_not_ingested")
    eligible = list(
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
            .order_by(AssessmentEvidence.id)
        )
    )
    qualification = evaluate(eligible, profile, prefs)
    if administration["identity"] == "verified":
        gaps = [gap for gap in gaps if gap != "business_identity"]
        qualification["qualification_gaps"] = [
            g for g in qualification["qualification_gaps"] if g["code"] != "business_identity"
        ]
        qualification["recommendations"] = [
            g["recommendation"] for g in qualification["qualification_gaps"]
        ]
    policy = introduction_policy(
        MANDATORY_VERIFICATIONS,
        ("business_identity",) if administration["identity"] == "verified" else (),
    )
    policy["discovery_eligible"] = (
        administration["approval"] != "rejected" and administration["access"] == "active"
    )
    policy["introduction_allowed"] = False
    policy["missing_requirements"] = ["mutual_consent_workflow"]
    return {
        "organization_id": business_id,
        "profile": {
            "classification": "self_reported",
            "values": {key: getattr(profile, key) for key in ("name", "sector", "country", "goal")}
            if profile
            else None,
        },
        "market_preferences": {
            "classification": "self_reported",
            "values": [{"country": p.country, "partner_type": p.partner_type} for p in prefs],
        },
        "assessment_evidence": [
            {
                "id": r.id,
                "assessment_id": r.assessment_id,
                "classification": "self_reported",
                "extraction_version": r.extraction_version,
            }
            for r in evidence
        ],
        "independently_verified_evidence": [
            {"claim": "business_identity", "source": "platform_owner_decision"}
        ]
        if administration["identity"] == "verified"
        else [],
        "supporting_evidence_status": "not_implemented",
        "disclosed_gaps": gaps,
        "policy": policy,
        "administration": administration,
        "score": None,
        "matching_algorithm": "not_implemented",
        **qualification,
    }
