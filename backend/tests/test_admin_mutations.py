from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_admin import owner as owner
from test_business import INPUT, ORIGIN, login
from workspace_fixtures import businesses as businesses
from workspace_fixtures import setup as setup

from app.admin.models import AdministrativeDecision, BusinessAdministration
from app.admin.mutation_schemas import StatusDecision
from app.admin.mutations import mutate
from app.security import Principal


def decision(action, version=0, **kwargs):
    return dict(
        action=action,
        expected_version=version,
        request_id=str(uuid4()),
        reason="Reviewed isolated test record",
        **kwargs,
    )


@pytest.mark.parametrize("method,path", [("post", "decisions"), ("put", "profile")])
def test_owner_auth_csrf_and_no_identity_spoof(setup, businesses, method, path):
    client = setup[0]
    url = f"/api/admin/businesses/{businesses[0]}/{path}"
    client.cookies.clear()
    payload = (
        decision("approve")
        if path == "decisions"
        else dict(expected_version=0, request_id=str(uuid4()), reason="Test", profile=INPUT)
    )
    assert getattr(client, method)(url, json=payload, headers=ORIGIN).status_code == 401
    client = login(setup, "bob")
    assert (
        getattr(client, method)(
            url, json=payload, headers={**ORIGIN, "X-User-ID": "alice"}
        ).status_code
        == 403
    )


def test_independent_states_audit_validation_retry_and_conflict(owner, businesses, setup):
    url = f"/api/admin/businesses/{businesses[0]}"
    assert owner.post(url + "/decisions", json=decision("approve")).status_code == 403
    payload = decision("approve")
    first = owner.post(url + "/decisions", json=payload, headers=ORIGIN)
    assert first.status_code == 200
    assert owner.post(url + "/decisions", json=payload, headers=ORIGIN).json()["replayed"]
    assert (
        owner.post(
            url + "/decisions", json={**payload, "reason": "Changed"}, headers=ORIGIN
        ).status_code
        == 409
    )
    assert (
        owner.post(url + "/decisions", json=decision("reject"), headers=ORIGIN).status_code == 409
    )
    state = owner.get(url).json()["administration"]
    assert state == dict(approval="approved", identity="unverified", access="active", version=1)
    assert (
        owner.post(
            url + "/decisions", json=decision("verify_identity", 1), headers=ORIGIN
        ).status_code
        == 422
    )
    actions = [
        ("verify_identity", {"evidence_references": ["local-review:test-record"]}),
        ("suspend", {}),
        ("reject", {}),
        ("revoke_identity", {}),
        ("reactivate", {}),
        ("approve", {}),
    ]
    for version, (action, extra) in enumerate(actions, 1):
        assert (
            owner.post(
                url + "/decisions", json=decision(action, version, **extra), headers=ORIGIN
            ).status_code
            == 200
        )
    assert (
        owner.post(url + "/decisions", json=decision("approve", 7), headers=ORIGIN).status_code
        == 409
    )
    history = owner.get(url + "/history").json()
    assert history["total"] == 7
    assert all(
        r["actor_id"] == "alice" and r["created_at"] and r["reason"] for r in history["items"]
    )
    with Session(setup[1]) as db:
        audit = db.get(AdministrativeDecision, first.json()["decision_id"])
        assert (
            audit.previous_values["approval"] == "pending"
            and audit.new_values["approval"] == "approved"
        )
        audit.reason = "Tamper"
        with pytest.raises(ValueError, match="append-only"):
            db.commit()
        db.rollback()
    assert (
        owner.post(
            url + "/decisions", json={**decision("reject", 7), "actor_id": "bob"}, headers=ORIGIN
        ).status_code
        == 422
    )
    assert (
        owner.post(
            url + "/decisions", json={**decision("reject", 7), "reason": "  "}, headers=ORIGIN
        ).status_code
        == 422
    )


def test_profile_edit_audit_and_identity_invalidation(owner, businesses):
    url = f"/api/admin/businesses/{businesses[0]}"
    for version, action in enumerate(["approve", "verify_identity"]):
        payload = decision(action, version, evidence_references=["independent:review"])
        assert owner.post(url + "/decisions", json=payload, headers=ORIGIN).status_code == 200
    body = dict(
        profile={**INPUT, "name": "Updated Name"},
        expected_version=2,
        request_id=str(uuid4()),
        reason="Correct independently reviewed identity",
    )
    assert owner.put(url + "/profile", json=body, headers=ORIGIN).status_code == 200
    current = owner.get(url).json()
    assert (
        current["name"] == "Updated Name" and current["administration"]["identity"] == "unverified"
    )
    assert current["administration"]["approval"] == "pending"
    history = owner.get(url + "/history").json()["items"][0]
    assert history["previous_values"]["profile"]["name"] == INPUT["name"]
    assert history["new_values"]["profile"]["name"] == "Updated Name"
    assert (
        owner.put(
            url + "/profile", json={**body, "profile": {**INPUT, "name": " "}}, headers=ORIGIN
        ).status_code
        == 422
    )


def test_transaction_rollback_and_concurrent_requests(owner, businesses, setup, monkeypatch):
    engine = setup[1]
    with Session(engine) as db:
        original_flush = db.flush

        def failing_flush(*args, **kwargs):
            if any(isinstance(r, AdministrativeDecision) for r in db.new):
                raise RuntimeError("Test audit failure")
            return original_flush(*args, **kwargs)

        monkeypatch.setattr(db, "flush", failing_flush)
        with pytest.raises(RuntimeError):
            mutate(
                db,
                Principal("alice"),
                setup[0].app.state.settings,
                businesses[0],
                StatusDecision(**decision("approve")),
            )
    with Session(engine) as db:
        assert db.get(BusinessAdministration, businesses[0]) is None
    payload = StatusDecision(**decision("approve"))

    def run(_):
        with Session(engine) as db:
            return mutate(
                db, Principal("alice"), setup[0].app.state.settings, businesses[0], payload
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))
    assert sorted(r["replayed"] for r in results) == [False, True]
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(AdministrativeDecision)) == 1
