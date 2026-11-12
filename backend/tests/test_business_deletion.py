from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from test_admin import owner as owner
from test_business import ORIGIN, login
from workspace_fixtures import businesses as businesses
from workspace_fixtures import setup as setup

from app.admin.deletion import service
from app.admin.deletion.models import DeletionEvent, DeletionOperation
from app.admin.models import AdministrativeDecision
from app.models import BusinessProfile, Membership, Organization, User


def confirmation(client, business):
    response = client.get(f"/api/admin/businesses/{business}/deletion/preview")
    assert response.status_code == 200
    preview = response.json()
    return dict(
        request_id=str(uuid4()),
        business_name=preview["business_name"],
        expected_version=preview["version"],
        preview_token=preview["preview_token"],
        reason="Remove isolated fictional test business",
    )


def test_confirmation_auth_csrf_and_stale_preview(owner, setup, businesses):
    url = f"/api/admin/businesses/{businesses[0]}/deletion"
    body = confirmation(owner, businesses[0])
    assert owner.post(url, json=body).status_code == 403
    for field, value in [
        ("business_name", "Wrong"),
        ("expected_version", 99),
        ("preview_token", "0" * 64),
    ]:
        assert owner.post(url, json={**body, field: value}, headers=ORIGIN).status_code == 409
    assert owner.post(url, json={**body, "reason": " "}, headers=ORIGIN).status_code == 422
    assert owner.post(url, json={**body, "actor_id": "bob"}, headers=ORIGIN).status_code == 422
    login(setup, "bob")
    assert owner.get(url + "/preview").status_code == 403
    assert owner.post(url, json=body, headers=ORIGIN).status_code == 403
    owner.cookies.clear()
    assert owner.post(url, json=body, headers=ORIGIN).status_code == 401


def test_local_deletion_idempotency_tombstone_audit_and_isolation(owner, setup, businesses):
    business = businesses[0]
    body = confirmation(owner, business)
    url = f"/api/admin/businesses/{business}/deletion"
    response = owner.post(url, json=body, headers=ORIGIN)
    assert response.status_code == 200
    op = response.json()["operation"]
    assert (
        op["state"] == "completed"
        and op["local_data_removed"]
        and op["salesforce_outcome"] == "not_linked"
    )
    assert owner.post(url, json=body, headers=ORIGIN).json()["operation"]["id"] == op["id"]
    assert (
        owner.post(url, json={**body, "request_id": str(uuid4())}, headers=ORIGIN).status_code
        == 409
    )
    assert owner.get(url).json()["operation"]["completed_at"]
    assert (
        owner.get(f"/api/admin/businesses/{business}/history").json()["items"][0]["action"]
        == "delete_requested"
    )
    with Session(setup[1]) as db:
        assert (
            db.scalar(select(BusinessProfile).where(BusinessProfile.organization_id == business))
            is None
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(Membership)
                .where(Membership.organization_id == business)
            )
            == 0
        )
        assert db.get(Organization, business).name == "Deleted business"
        assert db.get(Organization, businesses[1]).name != "Deleted business"
        assert db.get(User, "alice") is not None
        assert db.scalar(select(func.count()).select_from(DeletionOperation)) == 1
        event = db.scalar(select(DeletionEvent))
        db.delete(event)
        with pytest.raises(ValueError, match="append-only"):
            db.flush()
        db.rollback()
    assert owner.get("/api/admin/dashboard").json()["workspaces"] == 1
    assert owner.get(f"/api/businesses/{business}").status_code == 403


def test_local_failure_leaves_durable_lock_and_retry(owner, setup, businesses, monkeypatch):
    url = f"/api/admin/businesses/{businesses[0]}/deletion"
    body = confirmation(owner, businesses[0])
    original = service.purge

    def fail(db, business_id):
        original(db, business_id)
        raise OperationalError("test", {}, None)

    monkeypatch.setattr(service, "purge", fail)
    assert owner.post(url, json=body, headers=ORIGIN).status_code == 503
    op = owner.get(url).json()["operation"]
    assert op["state"] == "local_pending"
    assert owner.get(f"/api/businesses/{businesses[0]}").status_code == 403
    assert owner.get(f"/api/admin/businesses/{businesses[0]}").status_code == 200
    assert (
        owner.post(
            f"/api/admin/businesses/{businesses[0]}/decisions",
            json=dict(
                action="reactivate", expected_version=1, request_id=str(uuid4()), reason="Test"
            ),
            headers=ORIGIN,
        ).status_code
        == 409
    )
    monkeypatch.setattr(service, "purge", original)
    assert (
        owner.post(url + "/retry", json={"operation_id": op["id"]}, headers=ORIGIN).json()[
            "operation"
        ]["state"]
        == "completed"
    )
    wrong = owner.post(
        f"/api/admin/businesses/{businesses[1]}/deletion/retry",
        json={"operation_id": op["id"]},
        headers=ORIGIN,
    )
    assert wrong.status_code == 404


def test_all_owned_dependencies_removed_in_fk_order(owner, setup, businesses):
    from datetime import datetime, timezone

    from sqlalchemy import text

    from app.assessments.models import BusinessAssessment
    from app.models import (
        BusinessEvent,
        IntroductionRequest,
        MarketPreference,
        MatchExplanation,
        Opportunity,
    )
    from app.qualification.models import AssessmentEvidence

    business = businesses[0]
    with Session(setup[1]) as db:
        opportunity = Opportunity(organization_id=business, title="Fictional opportunity")
        db.add(opportunity)
        db.flush()
        db.add_all(
            [
                MatchExplanation(
                    organization_id=business,
                    opportunity_id=opportunity.id,
                    explanation="Fictional",
                    provenance="test",
                ),
                IntroductionRequest(
                    organization_id=business,
                    opportunity_id=opportunity.id,
                    message="Fictional introduction",
                ),
                MarketPreference(organization_id=business, country="Ghana", partner_type="Buyer"),
                BusinessEvent(organization_id=business, title="Fictional event", country="Ghana"),
            ]
        )
        # A legacy shared-link result has no bound Lead; no remote record is inferred or deleted.
        stamp = datetime.now(timezone.utc)
        assessment = BusinessAssessment(
            organization_id=business,
            business_id=business,
            initiated_by="alice",
            assessment_type="test",
            provider_survey_id="test",
            provider_logical_id="test",
            status="completed_verified",
            provider_response_id="test-legacy-result",
            completed_at=stamp,
            synchronized_at=stamp,
        )
        db.add(assessment)
        db.flush()
        db.add(
            AssessmentEvidence(
                organization_id=business,
                assessment_id=assessment.id,
                provider_response_id="test-legacy-result",
                extraction_version="test",
                content_hash="a" * 64,
                answers=[],
                gaps=[],
            )
        )
        db.commit()
    body = confirmation(owner, business)
    result = owner.post(f"/api/admin/businesses/{business}/deletion", json=body, headers=ORIGIN)
    assert result.json()["operation"]["state"] == "completed"
    with Session(setup[1]) as db:
        from app.admin.deletion.dependencies import PURGE_ORDER

        assert all(
            db.scalar(
                select(func.count()).select_from(model).where(model.organization_id == business)
            )
            == 0
            for model in PURGE_ORDER
        )
        assert list(db.execute(text("PRAGMA foreign_key_check"))) == []


def test_concurrent_confirmation_has_one_operation_and_no_duplicate_audit(owner, setup, businesses):
    from concurrent.futures import ThreadPoolExecutor

    from app.admin.deletion.schemas import DeleteConfirmation
    from app.security import Principal

    body = DeleteConfirmation(**confirmation(owner, businesses[0]))

    def run(_):
        with Session(setup[1]) as db:
            return service.initiate(
                db,
                Principal("alice"),
                setup[0].app.state.settings,
                businesses[0],
                body,
                setup[0].app.state.salesforce_client,
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        operations = list(pool.map(run, range(2)))
    assert operations[0] == operations[1]
    with Session(setup[1]) as db:
        assert db.scalar(select(func.count()).select_from(DeletionOperation)) == 1
        assert db.scalar(select(func.count()).select_from(AdministrativeDecision)) == 1
