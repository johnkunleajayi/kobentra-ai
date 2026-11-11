import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import select

from ..assessments.models import BusinessAssessment
from ..salesforce.client import SalesforceError
from ..security import scoped_get
from ..workspace.transactions import tenant_write
from .extraction import EvidenceConflict, extract
from .models import AssessmentEvidence
from .provider import MAPPING, fetch_answers


def snapshot(db, principal, business_id, assessment_id):
    scoped_get(db, BusinessAssessment, principal, business_id, assessment_id)
    row = db.scalar(
        select(AssessmentEvidence).where(
            AssessmentEvidence.organization_id == business_id,
            AssessmentEvidence.assessment_id == assessment_id,
            AssessmentEvidence.extraction_version == MAPPING["extraction_version"],
        )
    )
    if row is None:
        raise HTTPException(404, "No ingested evidence")
    return serialize(row)


def serialize(row):
    return {
        "id": row.id,
        "organization_id": row.organization_id,
        "assessment_id": row.assessment_id,
        "provider_response_id": row.provider_response_id,
        "extraction_version": row.extraction_version,
        "evidence_kind": row.evidence_kind,
        "answers": row.answers,
        "gaps": row.gaps,
        "ingested_at": row.ingested_at,
    }


def ingest(db, principal, business_id, assessment_id, client):
    with tenant_write(db, principal, business_id):
        record = scoped_get(db, BusinessAssessment, principal, business_id, assessment_id)
        if (
            record.integration_mode != "salesforce_flow"
            or record.status != "completed_verified"
            or not record.salesforce_lead_id
            or not record.provider_response_id
            or not record.completed_at
            or record.provider_survey_id != MAPPING["survey_id"]
        ):
            raise HTTPException(409, "Only verified native assessments can be ingested")
        if not record.dispatch_payload or record.dispatch_payload.get("instance") != client.origin:
            raise HTTPException(409, "Salesforce source organization changed")
        try:
            rows, links, choices = fetch_answers(client, record)
            answers, gaps = extract(record.provider_response_id, rows, links, choices)
            digest = hashlib.sha256(
                json.dumps(
                    {"answers": answers, "gaps": gaps}, sort_keys=True, allow_nan=False
                ).encode()
            ).hexdigest()
        except (SalesforceError, EvidenceConflict, ValueError, TypeError, KeyError, AttributeError):
            raise HTTPException(
                409,
                "Assessment source is incomplete, malformed or changed; evidence not overwritten",
            ) from None
        existing = db.scalar(
            select(AssessmentEvidence).where(
                AssessmentEvidence.organization_id == business_id,
                AssessmentEvidence.assessment_id == assessment_id,
                AssessmentEvidence.extraction_version == MAPPING["extraction_version"],
            )
        )
        if existing:
            if (
                existing.content_hash != digest
                or existing.provider_response_id != record.provider_response_id
            ):
                raise HTTPException(
                    409, "Evidence conflict requires review; existing snapshot retained"
                )
            return serialize(existing), False
        row = AssessmentEvidence(
            organization_id=business_id,
            assessment_id=assessment_id,
            provider_response_id=record.provider_response_id,
            extraction_version=MAPPING["extraction_version"],
            content_hash=digest,
            answers=answers,
            gaps=gaps,
        )
        db.add(row)
        db.flush()
        result = serialize(row)
    return result, True
