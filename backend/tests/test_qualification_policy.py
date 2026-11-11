import pytest
from evidence_fixtures import PARENT
from evidence_fixtures import businesses as businesses
from evidence_fixtures import evidence as evidence
from evidence_fixtures import setup as setup
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_business import ORIGIN

from app.assessments.models import BusinessAssessment
from app.qualification.models import AssessmentEvidence
from app.qualification.policy import introduction_policy, require_introduction_evidence
from app.security import Principal


def test_discovery_gaps_and_mandatory_introduction_gate(evidence, setup, businesses):
    client, url, _, _ = evidence
    client.post(url + "/ingest", json={}, headers=ORIGIN)
    response = client.get(f"/api/businesses/{businesses[0]}/qualification")
    body = response.json()
    assert body["policy"]["discovery_eligible"] is True
    assert body["policy"]["introduction_allowed"] is False
    assert "business_identity" in body["disclosed_gaps"]
    assert body["independently_verified_evidence"] == [] and body["score"] is None
    assert body["profile"]["classification"] == "self_reported"
    with Session(setup[1]) as db:
        with pytest.raises(HTTPException) as exc:
            require_introduction_evidence(db, Principal("alice"), businesses[0])
        assert exc.value.status_code == 409
    assert (
        introduction_policy(["identity", "license"], ["identity"])["introduction_allowed"] is False
    )
    assert introduction_policy(["identity"], ["identity"])["introduction_allowed"] is True


def test_database_rejects_cross_tenant_evidence(evidence, setup, businesses):
    _, _, _, assessment = evidence
    with Session(setup[1]) as db:
        db.add(
            AssessmentEvidence(
                organization_id=businesses[1],
                assessment_id=assessment,
                provider_response_id=PARENT,
                extraction_version="sample",
                content_hash="0" * 64,
                answers=[],
                gaps=[],
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


@pytest.mark.parametrize(
    "mode,status",
    [("shared_public_link", "completed_verified"), ("salesforce_flow", "launch_requested")],
)
def test_nonverified_or_legacy_assessment_rejected(evidence, setup, mode, status):
    client, url, _, id_ = evidence
    with Session(setup[1]) as db:
        row = db.get(BusinessAssessment, id_)
        row.integration_mode = mode
        row.status = status
        if status != "completed_verified":
            row.provider_response_id = row.completed_at = row.synchronized_at = None
        db.commit()
    assert client.post(url + "/ingest", json={}, headers=ORIGIN).status_code == 409


def test_query_order_does_not_define_question_identity(evidence):
    client, url, source, _ = evidence
    before = client.post(url + "/ingest", json={}, headers=ORIGIN).json()
    source.rows.reverse()
    source.links.reverse()
    source.choices.reverse()
    after = client.post(url + "/ingest", json={}, headers=ORIGIN)
    assert after.status_code == 200 and after.json()["id"] == before["id"]
