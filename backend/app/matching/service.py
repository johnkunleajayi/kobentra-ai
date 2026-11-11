from fastapi import HTTPException
from sqlalchemy import select

from ..models import BusinessProfile
from ..qualification.policy import MANDATORY_VERIFICATIONS, foundation, introduction_policy
from ..security import authorize
from . import repository
from .engine import RULES, compare, normalized


def matches(db, principal, business_id, published_ids):
    authorize(db, principal, business_id)
    source = db.scalar(
        select(BusinessProfile).where(BusinessProfile.organization_id == business_id)
    )
    if source is None:
        raise HTTPException(404, "Business profile not found")
    qualification = foundation(db, principal, business_id)
    if not qualification["policy"]["discovery_eligible"]:
        raise HTTPException(403, "Discovery is not permitted")
    candidates = []
    source_inputs = repository.inputs(db, source)
    disputed = set(qualification["confidence"]["conflicting_claims"])
    # Only the requester's own evidence is consulted. Candidate private evidence is never read.
    if disputed & {"registered_name", "primary_country"}:
        source_inputs["conflicts"] = list(RULES["weights"])
    elif "industry" in disputed:
        source_inputs["conflicts"] = ["industry_capability"]
    for profile in repository.profiles(db, business_id, published_ids):
        policy = introduction_policy(MANDATORY_VERIFICATIONS, ())
        if not policy["discovery_eligible"]:
            continue
        # Same-country businesses are outside this cross-border discovery endpoint.
        if not normalized(profile.country) or normalized(profile.country) == normalized(
            source.country
        ):
            continue
        result = compare(source_inputs, repository.inputs(db, profile))
        candidates.append(
            {
                "partner": {
                    "business_id": profile.organization_id,
                    "name": profile.name,
                    "sector": profile.sector,
                    "country": profile.country,
                },
                "compatibility": result,
                "qualification_gaps": [
                    "Independent business identity is unverified.",
                    "Capabilities, operational suitability and timing are not established for discovery.",
                ],
                "introduction_eligibility": {
                    "allowed": False,
                    "missing_verifications": policy["missing_verifications"],
                    "reason": "Both businesses require independent identity verification and consent.",
                },
            }
        )
    candidates.sort(
        key=lambda m: (
            m["compatibility"]["score"] is None,
            -(m["compatibility"]["score"] or 0),
            m["partner"]["business_id"],
        )
    )
    return {
        "business_id": business_id,
        "rules_version": RULES["version"],
        "matches": candidates,
        "requester_qualification_gaps": qualification["qualification_gaps"],
        "directory_status": "curated_allowlist" if published_ids else "not_configured",
    }
