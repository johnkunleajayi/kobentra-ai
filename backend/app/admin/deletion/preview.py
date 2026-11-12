from fastapi import HTTPException
from sqlalchemy import select

from ...assessments.models import BusinessAssessment
from ...models import BusinessProfile
from ..eligibility import status
from .dependencies import dependencies
from .salesforce import digest, target_for


def preview(db, business_id, client):
    profile = db.scalar(
        select(BusinessProfile).where(BusinessProfile.organization_id == business_id)
    )
    if profile is None:
        raise HTTPException(404, "Business not found")
    assessments = list(
        db.scalars(
            select(BusinessAssessment).where(BusinessAssessment.organization_id == business_id)
        )
    )
    if any(
        not a.salesforce_lead_id
        and (a.dispatch_payload or a.correlation_id or a.dispatch_started_at)
        for a in assessments
    ):
        raise HTTPException(409, "Resolve unbound dispatch evidence before deletion")
    if any(
        a.dispatch_state in {"sending", "uncertain"}
        or (a.dispatch_state and not a.salesforce_lead_id)
        for a in assessments
    ):
        raise HTTPException(409, "Resolve outstanding dispatch before deletion")
    linked = [a for a in assessments if a.salesforce_lead_id]
    if len(linked) > 1:
        raise HTTPException(409, "Multiple linked Leads require separately reviewed deletion scope")
    target = target_for(client, linked[0]) if linked else None
    counts = dependencies(db, business_id)
    state = status(db, business_id)
    result = {
        "business_id": business_id,
        "business_name": profile.name,
        "version": state["version"],
        "dependencies": counts,
        "salesforce_target": target,
        "salesforce_deletion_policy": "recycle_bin",
        "implications": [
            "Business operations will be locked immediately.",
            "Local business-owned data is removed after exact linked Lead Recycle Bin deletion is verified, or when no Lead is linked.",
            "Platform audit history and an anonymized organization tombstone are retained.",
            "The linked Salesforce Lead is moved to the recoverable Salesforce Recycle Bin, not permanently purged.",
        ],
    }
    result["preview_token"] = digest(result)
    return result
