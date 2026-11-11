from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from ..models import BusinessProfile
from ..salesforce.client import SalesforceError
from ..salesforce.results import sf_id
from ..security import scoped_get
from ..workspace.transactions import tenant_write
from .models import BusinessAssessment
from .schemas import AssessmentSummary

SURVEY_ID = "a0Zaj00000JUZOnEAP"


def marker(record):
    return f"Kobentra assessment {record.id} correlation {record.correlation_id}"


def dispatch(db, principal, business_id, assessment_id, data, settings, client):
    if not settings.salesforce_dispatch_enabled:
        raise HTTPException(503, "Salesforce dispatch is disabled")
    with tenant_write(db, principal, business_id):
        record = scoped_get(db, BusinessAssessment, principal, business_id, assessment_id)
        if record.status == "completed_verified":
            raise HTTPException(409, "Assessment already completed")
        if record.integration_mode != "salesforce_flow":
            raise HTTPException(409, "Start a native assessment; legacy records cannot be rebound")
        if record.dispatch_state:
            previous = record.dispatch_payload["lead"]
            if previous["LastName"] != data.last_name or previous["Email"] != data.email:
                raise HTTPException(409, "Dispatch recipient is already fixed")
            return AssessmentSummary.model_validate(record)
        if (
            not client.origin
            or not settings.salesforce_client_id
            or not settings.salesforce_client_secret
        ):
            raise HTTPException(503, "Salesforce is not configured")
        profile = db.scalar(
            select(BusinessProfile).where(BusinessProfile.organization_id == business_id)
        )
        if profile is None:
            raise HTTPException(409, "Business profile is missing")
        record.correlation_id = str(uuid4())
        record.integration_mode = "salesforce_flow"
        record.provider_survey_id = SURVEY_ID
        record.dispatch_state = "sending"
        record.dispatch_started_at = datetime.now(timezone.utc)
        record.dispatch_payload = {
            "instance": client.origin,
            "lead": {
                "LastName": data.last_name,
                "Email": data.email,
                "Company": profile.name,
                "Country": profile.country,
                "Description": marker(record),
                "Kobentra_Assessment_Requested__c": True,
            },
        }
        payload = record.dispatch_payload["lead"]
    # Commit the durable send claim BEFORE the external POST. Never replay this POST
    # on another request, including a crash or lost response after remote commit.
    try:
        created = client.request("POST", "/services/data/v68.0/sobjects/Lead", json=payload)
        lead_id = sf_id(created["id"])
        if not created.get("success") or not lead_id.startswith("00Q"):
            raise SalesforceError("Invalid Lead creation response")
    except (SalesforceError, KeyError, TypeError):
        with tenant_write(db, principal, business_id):
            record = scoped_get(db, BusinessAssessment, principal, business_id, assessment_id)
            if record.dispatch_state == "sending":
                record.dispatch_state = "uncertain"
            db.flush()
            return AssessmentSummary.model_validate(record)
    with tenant_write(db, principal, business_id):
        record = scoped_get(db, BusinessAssessment, principal, business_id, assessment_id)
        if record.salesforce_lead_id and record.salesforce_lead_id != lead_id:
            raise HTTPException(409, "Conflicting Lead evidence requires review")
        record.salesforce_lead_id, record.dispatch_state = lead_id, "sent"
        if record.status != "completed_verified":
            record.status = "launch_requested"
        db.flush()
        return AssessmentSummary.model_validate(record)


def reconcile_lead(record, client):
    if record.dispatch_payload["instance"] != client.origin:
        raise SalesforceError("Salesforce organization configuration changed")
    expected = record.dispatch_payload["lead"]
    if record.salesforce_lead_id:
        lead_id = sf_id(record.salesforce_lead_id)
        rows = [client.request("GET", f"/services/data/v68.0/sobjects/Lead/{lead_id}")]
    else:
        stamp = record.dispatch_started_at
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        since = (stamp.astimezone(timezone.utc) - timedelta(minutes=5)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        # Description is a long-text field, not SOQL-filterable. Enumerate recent
        # accessible Leads and compare the exact opaque marker locally. Pagination
        # must finish; an empty/incomplete scan NEVER authorizes another POST.
        rows = client.query(
            f"SELECT Id, Description, LastName, Email, Company FROM Lead WHERE CreatedDate >= {since}"
        )
    matched = [row for row in rows if row.get("Description") == marker(record)]
    if len(matched) > 1:
        raise SalesforceError("Duplicate correlated Leads require review")
    if not matched:
        return None
    row = matched[0]
    if any(row.get(key) != expected[key] for key in ("Company", "LastName", "Email")):
        raise SalesforceError("Lead correlation evidence mismatch")
    found = sf_id(row.get("Id"))
    if not found.startswith("00Q") or (
        record.salesforce_lead_id and found != record.salesforce_lead_id
    ):
        raise SalesforceError("Lead identity mismatch")
    return found
