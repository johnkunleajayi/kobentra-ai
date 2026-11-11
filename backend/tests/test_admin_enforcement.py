import pytest
from sqlalchemy.orm import Session
from test_admin import owner as owner
from test_admin_mutations import decision
from test_business import INPUT, ORIGIN, login
from workspace_fixtures import businesses as businesses
from workspace_fixtures import setup as setup

from app.admin.models import BusinessAdministration
from app.qualification.policy import require_introduction_evidence
from app.security import Principal


def test_suspension_blocks_operations_but_admin_can_inspect(owner, setup, businesses):
    url = f"/api/admin/businesses/{businesses[0]}"
    assert (
        owner.post(url + "/decisions", json=decision("suspend"), headers=ORIGIN).status_code == 200
    )
    assert owner.get(url).status_code == 200
    for feature in ("", "/matches", "/market-preferences", "/assessments"):
        assert owner.get(f"/api/businesses/{businesses[0]}{feature}").status_code == 403
    assert (
        owner.post(
            f"/api/businesses/{businesses[0]}/assessments", json={}, headers=ORIGIN
        ).status_code
        == 403
    )
    assert owner.post("/api/businesses", json=INPUT, headers=ORIGIN).status_code == 403
    assert (
        owner.post(url + "/decisions", json=decision("reactivate", 1), headers=ORIGIN).status_code
        == 200
    )
    assert owner.get(f"/api/businesses/{businesses[0]}").status_code == 200


def test_approval_allowlist_suspension_and_rejection_are_all_enforced(owner, setup, businesses):
    from sqlalchemy import select

    from app.models import BusinessProfile

    with Session(setup[1]) as db:
        db.scalar(
            select(BusinessProfile).where(BusinessProfile.organization_id == businesses[1])
        ).country = "Nigeria"
        db.commit()
    setup[0].app.state.settings.matching_discovery_business_ids = [businesses[1]]
    matches = f"/api/businesses/{businesses[0]}/matches"
    url = f"/api/admin/businesses/{businesses[1]}"
    assert owner.get(matches).json()["matches"] == []
    for version, action in enumerate(["approve", "suspend", "reactivate", "reject"]):
        assert (
            owner.post(
                url + "/decisions", json=decision(action, version), headers=ORIGIN
            ).status_code
            == 200
        )
        assert len(owner.get(matches).json()["matches"]) == (
            1 if action in {"approve", "reactivate"} else 0
        )
    assert owner.get(f"/api/businesses/{businesses[1]}/matches").status_code == 403
    setup[0].app.state.settings.matching_discovery_business_ids = []
    assert (
        owner.post(url + "/decisions", json=decision("approve", 4), headers=ORIGIN).status_code
        == 200
    )
    assert owner.get(matches).json()["matches"] == []


def test_verification_is_independent_and_does_not_authorize_introduction(owner, setup, businesses):
    from fastapi import HTTPException

    url = f"/api/admin/businesses/{businesses[0]}"
    assert (
        owner.post(
            url + "/decisions",
            json=decision("verify_identity", evidence_references=["review:identity"]),
            headers=ORIGIN,
        ).status_code
        == 200
    )
    qualification = owner.get(f"/api/businesses/{businesses[0]}/qualification").json()
    assert qualification["administration"]["approval"] == "pending"
    assert not qualification["policy"]["introduction_allowed"]
    assert qualification["confidence"]["classification"] == "self_reported"
    with Session(setup[1]) as db:
        with pytest.raises(HTTPException) as exc:
            require_introduction_evidence(db, Principal("alice"), businesses[0])
        assert exc.value.status_code == 409
    login(setup, "bob")
    assert (
        setup[0]
        .post(url + "/decisions", json=decision("revoke_identity", 1), headers=ORIGIN)
        .status_code
        == 403
    )
    with Session(setup[1]) as db:
        assert db.get(BusinessAdministration, businesses[0]).identity == "verified"
