from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select

from ...salesforce.client import SalesforceError
from ..models import AdministrativeDecision, BusinessAdministration
from .dependencies import purge
from .models import DeletionEvent, DeletionOperation
from .preview import preview
from .salesforce import digest, lead, recycle
from .transactions import owner_transaction


def event(db, operation, actor_id, state, error=None):
    operation.state, operation.error_code = state, error
    db.add(
        DeletionEvent(operation_id=operation.id, actor_id=actor_id, state=state, error_code=error)
    )


def initiate(db, principal, settings, business_id, data, client):
    payload_hash = digest(data.model_dump(mode="json"))
    with owner_transaction(db, principal, settings, business_id):
        existing = db.scalar(
            select(DeletionOperation).where(DeletionOperation.organization_id == business_id)
        )
        if existing:
            if (
                existing.request_id != str(data.request_id)
                or existing.payload_hash != payload_hash
                or existing.actor_id != principal.user_id
            ):
                raise HTTPException(409, "Another deletion request already exists")
            return existing.id
        checked = preview(db, business_id, client)
        if (
            checked["business_name"] != data.business_name
            or checked["version"] != data.expected_version
            or checked["preview_token"] != data.preview_token
        ):
            raise HTTPException(409, "Deletion preview changed; review again")
        if checked["salesforce_target"] and not settings.salesforce_business_deletion_enabled:
            raise HTTPException(409, "Salesforce deletion is disabled pending integration review")
        state = db.get(BusinessAdministration, business_id)
        if state is None:
            state = BusinessAdministration(organization_id=business_id)
            db.add(state)
            db.flush()
        before = {k: getattr(state, k) for k in ("approval", "identity", "access", "version")}
        state.access, state.version = "suspended", state.version + 1
        operation = DeletionOperation(
            organization_id=business_id,
            actor_id=principal.user_id,
            request_id=str(data.request_id),
            payload_hash=payload_hash,
            reason=data.reason,
            target=checked["salesforce_target"],
            state="salesforce_pending" if checked["salesforce_target"] else "local_pending",
        )
        db.add(operation)
        db.flush()
        db.add(
            AdministrativeDecision(
                organization_id=business_id,
                actor_id=principal.user_id,
                action="delete_requested",
                reason=data.reason,
                evidence_references=[],
                previous_values=before,
                new_values={
                    "operation_id": operation.id,
                    "access": "suspended",
                    "version": state.version,
                },
                request_id=str(data.request_id),
                payload_hash=payload_hash,
            )
        )
        event(db, operation, principal.user_id, operation.state)
        result = operation.id
    return result


def advance(db, principal, settings, business_id, operation_id, client):
    with owner_transaction(db, principal, settings, business_id):
        operation = db.scalar(
            select(DeletionOperation).where(
                DeletionOperation.id == operation_id,
                DeletionOperation.organization_id == business_id,
            )
        )
        if operation is None:
            raise HTTPException(404, "Deletion operation not found")
        if operation.state == "completed":
            return
        if operation.target:
            if not settings.salesforce_business_deletion_enabled:
                event(
                    db,
                    operation,
                    principal.user_id,
                    "salesforce_retry",
                    "salesforce_deletion_disabled",
                )
                return
            try:
                recycle(client, operation.target)
            except (SalesforceError, ValueError, KeyError, TypeError, AttributeError):
                event(
                    db,
                    operation,
                    principal.user_id,
                    "salesforce_retry",
                    "salesforce_linkage_or_availability_error",
                )
                return
            # Commit remote verification separately; a later local rollback cannot lose it.
            # Legacy awaiting_permanent_purge operations take this same revalidation path.
            event(db, operation, principal.user_id, "local_pending")
    with owner_transaction(db, principal, settings, business_id) as org:
        operation = db.scalar(
            select(DeletionOperation).where(
                DeletionOperation.id == operation_id,
                DeletionOperation.organization_id == business_id,
            )
        )
        if operation.state == "completed":
            return
        if operation.state != "local_pending":
            raise HTTPException(409, "Deletion is not ready for local cleanup")
        if operation.target:
            try:
                if lead(client, operation.target)["IsDeleted"] is not True:
                    raise SalesforceError("Lead restored before local cleanup")
            except (SalesforceError, ValueError, KeyError, TypeError, AttributeError):
                event(
                    db,
                    operation,
                    principal.user_id,
                    "salesforce_retry",
                    "salesforce_linkage_or_availability_error",
                )
                return
        purge(db, business_id)
        org.name = "Deleted business"
        operation.completed_at = datetime.now(timezone.utc)
        event(db, operation, principal.user_id, "completed")


def operation_status(db, business_id):
    row = db.scalar(
        select(DeletionOperation).where(DeletionOperation.organization_id == business_id)
    )
    if row is None:
        return {"operation": None}
    events = list(
        db.scalars(
            select(DeletionEvent)
            .where(DeletionEvent.operation_id == row.id)
            .order_by(DeletionEvent.created_at.desc(), DeletionEvent.id)
            .limit(50)
        )
    )
    return {
        "operation": {
            "id": row.id,
            "business_id": business_id,
            "state": row.state,
            "error_code": row.error_code,
            "created_at": row.created_at,
            "completed_at": row.completed_at,
            "salesforce_outcome": "not_linked"
            if not row.target
            else "recycled_verified"
            if row.state in {"completed", "local_pending"}
            else "not_verified",
            "local_data_removed": row.state == "completed",
            "events": [
                {
                    "state": e.state,
                    "error_code": e.error_code,
                    "actor_id": e.actor_id,
                    "created_at": e.created_at,
                }
                for e in events
            ],
        }
    }
