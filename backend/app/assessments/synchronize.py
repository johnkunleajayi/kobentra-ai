from datetime import datetime, timezone

from fastapi import HTTPException

from ..salesforce.client import SalesforceError
from ..salesforce.results import completed_result
from ..security import scoped_get
from ..workspace.transactions import tenant_write
from .dispatch import reconcile_lead
from .models import BusinessAssessment
from .schemas import AssessmentSummary


def synchronize(db, principal, business_id, assessment_id, client):
    # Keep the tenant write lock while verifying and binding evidence, so two syncs
    # cannot bind contradictory results. All external reads have bounded timeouts.
    with tenant_write(db, principal, business_id):
        record = scoped_get(db, BusinessAssessment, principal, business_id, assessment_id)
        if record.integration_mode != "salesforce_flow" or not record.dispatch_state:
            raise HTTPException(409, "No native dispatch to synchronize")
        if record.status == "completed_verified":
            return AssessmentSummary.model_validate(record)
        try:
            lead = reconcile_lead(record, client)
            if lead:
                result = completed_result(client, lead, record.provider_survey_id)
                record.salesforce_lead_id, record.dispatch_state = lead, "sent"
                record.status = "launch_requested"
                if result:
                    response_id, completed_at = result
                    start = record.dispatch_started_at
                    if start.tzinfo is None:
                        start = start.replace(tzinfo=timezone.utc)
                    if completed_at < start:
                        raise SalesforceError("Completion predates dispatch")
                    record.provider_response_id = response_id
                    record.completed_at = completed_at
                    record.synchronized_at = datetime.now(timezone.utc)
                    record.status = "completed_verified"
            db.flush()
        except (SalesforceError, KeyError, TypeError, ValueError):
            raise HTTPException(
                503, "Salesforce evidence unavailable; no completion verified"
            ) from None
        return AssessmentSummary.model_validate(record)
