from fastapi import HTTPException
from sqlalchemy import select

from ..models import BusinessProfile, MarketPreference
from ..security import authorize
from .models import AssessmentEvidence

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

    No independent verification source is implemented yet. A completed survey is
    evidence of self-reporting, never evidence that identity/capabilities are true.
    """
    authorize(db, principal, business_id, write=True)
    policy = introduction_policy(MANDATORY_VERIFICATIONS, independently_verified=())
    if not policy["introduction_allowed"]:
        raise HTTPException(409, "Mandatory independent verification is missing")


def foundation(db, principal, business_id):
    authorize(db, principal, business_id)
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
        "independently_verified_evidence": [],
        "supporting_evidence_status": "not_implemented",
        "disclosed_gaps": gaps,
        "policy": introduction_policy(MANDATORY_VERIFICATIONS, ()),
        "score": None,
        "matching_algorithm": "not_implemented",
    }
