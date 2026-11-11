import pytest
from evidence_fixtures import evidence as evidence
from sqlalchemy import event
from sqlalchemy.orm import Session
from test_business import login
from workspace_fixtures import businesses as businesses
from workspace_fixtures import setup as setup

from app.models import Membership, User


@pytest.fixture
def owner(setup):
    with Session(setup[1]) as db:
        db.get(User, "alice").provider_subject = "test-google-sub-owner"
        db.get(User, "bob").provider_subject = "different-google-sub"
        db.commit()
    from pydantic import SecretStr

    setup[0].app.state.settings.platform_owner_google_subject = SecretStr("test-google-sub-owner")
    return login(setup)


@pytest.mark.parametrize(
    "path", ["dashboard", "users", "businesses", "businesses/00000000-0000-0000-0000-000000000000"]
)
def test_every_admin_endpoint_requires_owner(setup, path):
    client = setup[0]
    assert client.get("/api/admin/" + path).status_code == 401
    client = login(setup, "bob")
    response = client.get(
        "/api/admin/" + path,
        params={
            "user_id": "alice",
            "provider_subject": "test-google-sub-owner",
            "email": "a@example.invalid",
        },
        headers={"X-User-ID": "alice", "X-Platform-Admin": "true"},
    )
    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"


def test_configured_subject_only_and_safe_capability(owner, setup):
    client = owner
    me = client.get("/api/auth/me")
    assert me.json()["capabilities"] == {"platform_admin": True}
    assert "test-google-sub-owner" not in me.text
    assert me.headers["cache-control"] == "no-store"
    assert client.get("/api/admin/dashboard").status_code == 200
    setup[0].app.state.settings.platform_owner_google_subject = None
    assert client.get("/api/admin/dashboard").status_code == 403
    assert client.get("/api/auth/me").json()["capabilities"]["platform_admin"] is False


def test_email_or_missing_subject_never_grants_access(owner, setup):
    with Session(setup[1]) as db:
        db.get(User, "alice").provider_subject = None
        db.commit()
    assert owner.get("/api/admin/users").status_code == 403
    assert owner.get("/api/auth/me").json()["capabilities"]["platform_admin"] is False


def test_statistics_search_pagination_details_and_tenant_isolation(owner, setup, businesses):
    stats = owner.get("/api/admin/dashboard")
    assert stats.json()["users"] == 2
    assert stats.json()["businesses"] == stats.json()["workspaces"] == 2
    first = owner.get("/api/admin/users?page_size=1").json()
    second = owner.get("/api/admin/users?page_size=1&page=2").json()
    assert first["total"] == 2 and first["items"][0]["id"] != second["items"][0]["id"]
    assert first["items"][0]["created_at"] is None
    assert len(first["items"][0]["businesses"]) == 2
    assert owner.get("/api/admin/users?q=b@example.invalid").json()["total"] == 1
    assert owner.get("/api/admin/users?q=%25").json()["total"] == 0
    listed = owner.get("/api/admin/businesses?q=Second").json()
    assert listed["total"] == 1 and listed["items"][0]["owners"][0]["id"] == "alice"
    assert owner.get("/api/admin/businesses?page_size=1&page=2").json()["items"]
    assert owner.get("/api/admin/businesses?page=999").json()["items"] == []
    detail = owner.get(f"/api/admin/businesses/{businesses[0]}")
    assert detail.status_code == 200 and detail.json()["registered_at"] is None
    assert detail.json()["qualification"]["readiness"]["score"] is None
    assert all(
        secret not in detail.text
        for secret in ("provider_subject", "normalized_value", "dispatch_payload", "token_hash")
    )
    # Owner may use explicit admin reads, but cannot gain normal tenant membership.
    with Session(setup[1]) as db:
        db.get(Membership, ("alice", businesses[1])).user_id = "bob"
        db.commit()
    assert owner.get(f"/api/admin/businesses/{businesses[1]}").status_code == 200
    assert owner.get(f"/api/businesses/{businesses[1]}").status_code == 403
    assert login(setup, "bob").get("/api/admin/users").status_code == 403


@pytest.mark.parametrize(
    "query", ["page=0", "page_size=101", "page_size=-1", "page=x", "q=" + "a" * 101]
)
def test_bounds_validated(owner, query):
    assert owner.get("/api/admin/users?" + query).status_code == 422


def test_no_n_plus_one_queries(owner, setup, businesses):
    queries = []

    def capture(conn, cursor, statement, params, context, many):
        queries.append(statement)

    event.listen(setup[1], "before_cursor_execute", capture)
    try:
        assert owner.get("/api/admin/businesses").status_code == 200
    finally:
        event.remove(setup[1], "before_cursor_execute", capture)
    # Session auth + owner lookup + count + page + one batched owner lookup.
    assert len(queries) <= 5


def test_owner_revocation_is_authoritative(owner, setup):
    with Session(setup[1]) as db:
        db.get(User, "alice").provider_subject = "changed-sub"
        db.commit()
    assert owner.get("/api/admin/dashboard").status_code == 403


def test_detail_with_ingested_evidence_returns_only_summary(owner, evidence, businesses):
    from test_business import ORIGIN

    client, url, _, _ = evidence
    assert client.post(url + "/ingest", json={}, headers=ORIGIN).status_code == 201
    detail = client.get(f"/api/admin/businesses/{businesses[0]}")
    assert detail.status_code == 200
    assert detail.json()["qualification"]["completeness"]["answered"] == 10
    assert "Sample display" not in detail.text
    assert all(
        key not in detail.text
        for key in ("raw_value", "normalized_value", "provider_response_id", "salesforce_lead_id")
    )
