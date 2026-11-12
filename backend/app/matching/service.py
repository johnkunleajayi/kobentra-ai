from fastapi import HTTPException
from sqlalchemy import select

from ..models import BusinessProfile
from ..qualification.policy import foundation
from ..security import authorize
from . import repository
from .engine import RULES, compare, normalized


def matches(db, principal, business_id, published_ids=None):
    # published_ids is accepted for legacy callers but deliberately has no publication effect.
    authorize(db, principal, business_id)
    source = db.scalar(
        select(BusinessProfile).where(BusinessProfile.organization_id == business_id)
    )
    if source is None:
        raise HTTPException(404, "Business profile not found")
    qualification = foundation(db, principal, business_id)
    profiles = [source, *repository.profiles(db, business_id)]
    inputs = repository.batch_inputs(db, profiles)
    ready = inputs[business_id]["eligible"]
    candidates = []
    if ready:
        for profile in profiles[1:]:
            partner = inputs[profile.organization_id]
            if not partner["eligible"] or normalized(profile.country) == normalized(source.country):
                continue
            fit = compare(inputs[business_id], partner)
            if any(
                d["dimension"] == "geography" and d["state"] == "incompatible"
                for d in fit["dimensions"]
            ):
                continue
            candidates.append(
                {
                    "partner": {
                        "business_id": profile.organization_id,
                        "name": profile.name,
                        "sector": profile.sector,
                        "country": profile.country,
                    },
                    "compatibility": fit,
                    "qualification_gaps": [
                        d["reason"] for d in fit["dimensions"] if d["state"] == "unknown"
                    ],
                    "introduction_eligibility": {
                        "allowed": False,
                        "missing_verifications": [],
                        "reason": "Discovery is provisional. The separate consent-based introduction workflow is not enabled.",
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
        "readiness": qualification["readiness"],
        "assessment_completeness": qualification["completeness"],
        "directory_status": "automatic",
        "discovery_eligible": ready,
        "status_message": "Potential partners found."
        if candidates
        else "Your business is ready for partner discovery."
        if ready
        else "Complete your assessment and market preferences to discover partners.",
    }
