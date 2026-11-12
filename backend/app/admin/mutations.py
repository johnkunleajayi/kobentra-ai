import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from ..models import BusinessProfile, Organization, User
from .authorization import is_platform_owner
from .eligibility import values
from .models import AdministrativeDecision, BusinessAdministration

TRANSITIONS = {
    "approve": ("approval", "approved"),
    "reject": ("approval", "rejected"),
    "verify_identity": ("identity", "verified"),
    "revoke_identity": ("identity", "unverified"),
    "suspend": ("access", "suspended"),
    "reactivate": ("access", "active"),
}


def mutate(db, principal, settings, business_id, data):
    # Finish read-only dependency lookup, then recheck authority inside the locked transaction.
    db.rollback()
    payload = data.model_dump(mode="json")
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    try:
        with db.begin():
            if db.get_bind().dialect.name == "sqlite":
                db.execute(text("BEGIN IMMEDIATE"))
            org = db.scalar(
                select(Organization).where(Organization.id == business_id).with_for_update()
            )
            if not is_platform_owner(db.get(User, principal.user_id), settings):
                raise HTTPException(403, "Access denied")
            from .deletion.models import DeletionOperation
            if db.scalar(select(DeletionOperation.id).where(DeletionOperation.organization_id == business_id)):
                raise HTTPException(409, "Business deletion is pending or complete")
            profile = db.scalar(
                select(BusinessProfile).where(BusinessProfile.organization_id == business_id)
            )
            if not org or not profile:
                raise HTTPException(404, "Business not found")
            old = db.scalar(
                select(AdministrativeDecision).where(
                    AdministrativeDecision.organization_id == business_id,
                    AdministrativeDecision.request_id == str(data.request_id),
                )
            )
            if old:
                if old.payload_hash != digest or old.actor_id != principal.user_id:
                    raise HTTPException(409, "Conflicting administrative retry")
                return {
                    "decision_id": old.id,
                    "version": old.new_values["version"],
                    "replayed": True,
                }
            state = db.get(BusinessAdministration, business_id)
            if state is None:
                state = BusinessAdministration(organization_id=business_id)
                db.add(state)
                db.flush()
            if state.version != data.expected_version:
                raise HTTPException(409, "Administrative record changed; reload before deciding")
            before = values(state)
            if hasattr(data, "profile"):
                updates = data.profile.model_dump()
                before["profile"] = {k: getattr(profile, k) for k in updates}
                if before["profile"] == updates:
                    raise HTTPException(409, "Profile is unchanged")
                for key, value in updates.items():
                    setattr(profile, key, value)
                org.name = profile.name
                # Identity-bearing edits invalidate current identity verification.
                if any(before["profile"][k] != updates[k] for k in ("name", "country")):
                    state.identity = "unverified"
                    state.approval = "pending"
                action, refs = "edit_profile", []
            else:
                key, target = TRANSITIONS[data.action]
                if getattr(state, key) == target:
                    raise HTTPException(409, "Administrative transition is unchanged")
                setattr(state, key, target)
                action, refs = data.action, data.evidence_references
            state.version += 1
            after = values(state)
            if hasattr(data, "profile"):
                after["profile"] = data.profile.model_dump()
            decision = AdministrativeDecision(
                organization_id=business_id,
                actor_id=principal.user_id,
                action=action,
                reason=data.reason,
                evidence_references=refs,
                previous_values=before,
                new_values=after,
                request_id=str(data.request_id),
                payload_hash=digest,
            )
            db.add(decision)
            db.flush()
            result = {"decision_id": decision.id, "version": state.version, "replayed": False}
        return result
    except SQLAlchemyError:
        raise HTTPException(503, "Administrative write unavailable") from None
