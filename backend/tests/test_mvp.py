import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from evidence_fixtures import evidence as evidence
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_business import INPUT, ORIGIN, login
from test_qualification_scoring import sample
from workspace_fixtures import businesses as businesses
from workspace_fixtures import setup as setup

from app.admin.models import BusinessAdministration
from app.assessments.models import BusinessAssessment
from app.qualification.models import AssessmentEvidence
from app.qualification.provider import MAPPING


def test_newly_verified_completion_automatically_imports(evidence, setup, monkeypatch):
    from app.assessments import processing
    from app.assessments.schemas import AssessmentSummary

    client, url, source, assessment_id = evidence
    with Session(setup[1]) as db:
        record = db.get(BusinessAssessment, assessment_id)
        record.status = "launch_requested"
        response_id = record.provider_response_id
        record.provider_response_id = record.completed_at = record.synchronized_at = None
        db.commit()
    calls = []

    def verified(db, principal, business_id, id_, source):
        calls.append(id_)
        record = db.get(BusinessAssessment, id_)
        record.status = "completed_verified"
        record.provider_response_id = response_id
        record.completed_at = record.synchronized_at = source.stamp
        db.commit()
        return AssessmentSummary.model_validate(record)

    # Reconciliation's authoritative Salesforce validation has its own native tests.
    monkeypatch.setattr(processing, "synchronize", verified)
    response = client.post(url + "/sync", json={}, headers=ORIGIN)
    assert calls == [assessment_id]
    assert response.json()["processing_status"] == "ready"
    assert len(client.get(url + "/evidence").json()["answers"]) == 10


def test_concurrent_processing_keeps_one_immutable_snapshot(evidence, setup, businesses):
    from app.assessments.processing import process
    from app.security import Principal

    _, _, source, assessment_id = evidence

    def run(_):
        with Session(setup[1]) as db:
            return process(db, Principal("alice"), businesses[0], assessment_id, source)

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert all(r.processing_status == "ready" for r in pool.map(run, range(2)))
    with Session(setup[1]) as db:
        assert db.scalar(select(func.count()).select_from(AssessmentEvidence)) == 1


def test_completed_sync_imports_idempotently_without_dispatch(evidence, setup):
    client, url, source, _ = evidence
    before = len(source.queries)
    first = client.post(url + "/sync", json={}, headers=ORIGIN)
    assert first.status_code == 200 and first.json()["processing_status"] == "ready"
    assert first.json()["status"] == "completed_verified"
    queries = len(source.queries)
    assert queries > before
    assert (
        client.post(url + "/sync", json={}, headers=ORIGIN).json()["processing_status"] == "ready"
    )
    assert len(source.queries) == queries  # Persisted immutable snapshot: no further provider call.
    with Session(setup[1]) as db:
        assert db.scalar(select(func.count()).select_from(AssessmentEvidence)) == 1


def test_bounded_failure_preserves_completion_and_user_retry(evidence, setup, monkeypatch):
    from app.salesforce.client import SalesforceError

    client, url, source, assessment = evidence
    query = source.query
    calls = []

    def temporary(soql):
        calls.append(soql)
        raise SalesforceError("Temporary")

    monkeypatch.setattr(source, "query", temporary)
    response = client.post(url + "/sync", json={}, headers=ORIGIN)
    assert response.json()["processing_status"] == "retry"
    assert response.json()["status"] == "completed_verified"
    assert len(calls) == 2
    with Session(setup[1]) as db:
        assert db.get(BusinessAssessment, assessment).status == "completed_verified"
        assert db.scalar(select(func.count()).select_from(AssessmentEvidence)) == 0
    monkeypatch.setattr(source, "query", query)
    assert (
        client.post(url + "/sync", json={}, headers=ORIGIN).json()["processing_status"] == "ready"
    )


def seed(db, bid, country, industry, partnership, owner):
    from app.models import BusinessProfile, MarketPreference

    profile = db.scalar(select(BusinessProfile).where(BusinessProfile.organization_id == bid))
    profile.country, profile.sector = country, industry
    db.add(
        MarketPreference(
            organization_id=bid,
            country="Ghana" if country == "Nigeria" else "Nigeria",
            partner_type=partnership,
        )
    )
    parent = uuid4().hex[:18]
    stamp = datetime.now(timezone.utc)
    assessment = BusinessAssessment(
        organization_id=bid,
        business_id=bid,
        initiated_by=owner,
        assessment_type="partner_qualification",
        provider_survey_id=MAPPING["survey_id"],
        provider_logical_id="salesforce_flow",
        integration_mode="salesforce_flow",
        status="completed_verified",
        provider_response_id=parent,
        completed_at=stamp,
        synchronized_at=stamp,
        salesforce_lead_id="00Q" + uuid4().hex[:15],
    )
    db.add(assessment)
    db.flush()
    snapshot = sample()
    for answer in snapshot.answers:
        answer["parent_result_id"] = parent
        key = answer["key"]
        if key == "registered_name":
            answer["normalized_value"] = profile.name
        elif key == "cross_border_experience":
            answer["normalized_value"] = False
        elif key == "capabilities":
            answer["normalized_value"] = "Packaged food distribution and food production"
        elif key in {
            "primary_country",
            "industry",
            "partnership_types",
            "operational_capacity",
            "readiness_timeline",
        }:
            value = {
                "primary_country": country,
                "industry": industry,
                "partnership_types": partnership,
                "operational_capacity": "Growing — Able to handle increasing customer demand",
                "readiness_timeline": "Within 1–3 months",
            }[key]
            answer["normalized_value"] = [
                {"choice_id": "choice-" + key, "value": value, "label": value}
            ]
    db.add(
        AssessmentEvidence(
            organization_id=bid,
            assessment_id=assessment.id,
            provider_response_id=parent,
            extraction_version=MAPPING["extraction_version"],
            content_hash="a" * 64,
            answers=snapshot.answers,
            gaps=[],
        )
    )


def test_automatic_reciprocal_discovery_and_private_evidence(setup):
    client = login(setup)
    nig = client.post(
        "/api/businesses",
        json={**INPUT, "name": "Fictional Demo — Lagos Pantry Foods", "country": "Nigeria"},
        headers=ORIGIN,
    ).json()["organization_id"]
    login(setup, "bob")
    gha = client.post(
        "/api/businesses",
        json={**INPUT, "name": "Fictional Demo — Accra Distribution", "country": "Ghana"},
        headers=ORIGIN,
    ).json()["organization_id"]
    with Session(setup[1]) as db:
        assert db.get(BusinessAdministration, nig) is None
        assert db.get(BusinessAdministration, gha) is None
        seed(db, nig, "Nigeria", "Food & Beverage", "Distributors or resellers", "alice")
        seed(db, gha, "Ghana", "Wholesale & Distribution", "Suppliers or manufacturers", "bob")
        db.commit()
    for user, source, target in [("alice", nig, gha), ("bob", gha, nig)]:
        login(setup, user)
        r = client.get(f"/api/businesses/{source}/matches")
        assert r.status_code == 200 and r.json()["directory_status"] == "automatic"
        assert r.json()["discovery_eligible"] is True
        if user == "alice":
            Path("../work/discovery-fixture.json").write_text(
                json.dumps(r.json()), encoding="utf-8"
            )
        assert len(r.json()["matches"]) == 1
        match = r.json()["matches"][0]
        assert match["partner"]["business_id"] == target
        assert (
            match["compatibility"]["score"] == 100
            and match["compatibility"]["coverage_percent"] >= 60
        )
        assert match["introduction_eligibility"]["allowed"] is False
        assert all(
            x not in r.text
            for x in ("normalized_value", "raw_value", "question_result_id", "provider_response_id")
        )
        assert client.get(f"/api/businesses/{target}/qualification").status_code == 403
        gaps = client.get(f"/api/businesses/{source}/qualification").json()["qualification_gaps"]
        assert not any(
            g["code"] in {"business_identity", "cross_border_experience_development"} for g in gaps
        )
    with Session(setup[1]) as db:
        db.add(
            BusinessAdministration(
                organization_id=nig, approval="rejected", identity="unverified", access="active"
            )
        )
        db.commit()
    assert len(client.get(f"/api/businesses/{gha}/matches").json()["matches"]) == 1
    with Session(setup[1]) as db:
        db.get(BusinessAdministration, nig).access = "suspended"
        db.commit()
    assert client.get(f"/api/businesses/{gha}/matches").json()["matches"] == []
    login(setup, "alice")
    assert client.get(f"/api/businesses/{nig}/matches").status_code == 403


def test_incomplete_and_legacy_are_not_published(setup, businesses):
    client = login(setup)
    assert (
        client.get(f"/api/businesses/{businesses[0]}/matches").json()["discovery_eligible"] is False
    )
    assert client.get(f"/api/businesses/{businesses[0]}/matches").json()["matches"] == []


def test_processing_rejects_csrf_and_readonly_members(evidence, setup, businesses):
    from app.models import Membership

    client, url, source, _ = evidence
    assert (
        client.post(url + "/sync", json={}, headers={"Origin": "https://evil.invalid"}).status_code
        == 403
    )
    with Session(setup[1]) as db:
        db.get(Membership, ("alice", businesses[0])).role = "member"
        db.commit()
    assert client.post(url + "/sync", json={}, headers=ORIGIN).status_code == 403
    assert source.queries == []


def test_missing_answers_report_review_without_overwriting_snapshot(evidence, setup):
    client, url, source, _ = evidence
    source.rows.pop()  # Missing pinned question, not permission to fabricate its answer.
    result = client.post(url + "/sync", json={}, headers=ORIGIN)
    assert result.json()["status"] == "completed_verified"
    assert result.json()["processing_status"] == "needs_review"
    before = client.get(url + "/evidence").json()
    assert (
        client.post(url + "/sync", json={}, headers=ORIGIN).json()["processing_status"]
        == "needs_review"
    )
    assert client.get(url + "/evidence").json() == before
