"""Completion and ingestion are separate commits: import failures never undo completion."""

from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import select

from ..qualification.models import AssessmentEvidence
from ..qualification.provider import MAPPING
from ..qualification.scoring_inputs import collect
from ..qualification.service import EvidenceSourceUnavailable, ingest
from ..security import authorize, scoped_get
from .models import BusinessAssessment
from .schemas import AssessmentSummary
from .synchronize import synchronize


def imported_result(result, evidence):
    values, conflicts, issues = collect([evidence])
    complete = len(values) == 10 and not conflicts and not issues
    return result.model_copy(
        update={
            "processing_status": "ready" if complete else "needs_review",
            "processing_message": "Assessment processed. Discovery has been updated."
            if complete
            else "Completion verified. Imported answers need review before discovery; the original evidence is preserved.",
        }
    )


def process(db, principal, business_id, assessment_id, client):
    authorize(db, principal, business_id, write=True)
    record = scoped_get(db, BusinessAssessment, principal, business_id, assessment_id)
    if record.integration_mode != "salesforce_flow":
        raise HTTPException(
            409, "Legacy public assessments cannot be processed as native assessments"
        )
    result = AssessmentSummary.model_validate(record)
    db.rollback()
    if result.status != "completed_verified":
        result = synchronize(db, principal, business_id, assessment_id, client)
    if result.status != "completed_verified":
        return result.model_copy(
            update={
                "processing_status": "waiting",
                "processing_message": "Waiting for your submitted assessment.",
            }
        )
    existing = db.scalar(
        select(AssessmentEvidence).where(
            AssessmentEvidence.organization_id == business_id,
            AssessmentEvidence.assessment_id == assessment_id,
            AssessmentEvidence.provider_response_id == result.provider_response_id,
            AssessmentEvidence.extraction_version == MAPPING["extraction_version"],
        )
    )
    imported = imported_result(result, existing) if existing is not None else None
    db.rollback()
    if imported:
        return imported
    for attempt in range(2):
        try:
            evidence, _ = ingest(db, principal, business_id, assessment_id, client)
            return imported_result(result, SimpleNamespace(**evidence))
        except EvidenceSourceUnavailable:
            db.rollback()
            if attempt == 0:
                continue
            return result.model_copy(
                update={
                    "processing_status": "retry",
                    "processing_message": "Completion verified. Answers are temporarily unavailable; processing will retry.",
                }
            )
        except HTTPException as exc:
            db.rollback()
            if exc.status_code in {401, 403, 404}:
                raise
            return result.model_copy(
                update={
                    "processing_status": "retry" if exc.status_code == 503 else "needs_review",
                    "processing_message": "Completion verified. Answer processing needs a retry or source-data review; existing evidence is preserved.",
                }
            )
