from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth_sessions import create_session, revoke_session
from app.business import repository
from app.business.schemas import BusinessRegistration
from app.business.service import register_business
from app.config import Settings
from app.main import create_app
from app.models import Base, BusinessProfile, Membership, Organization, User

ORIGIN = {"Origin": "http://127.0.0.1:5173"}
INPUT = {"name": "Sample Cocoa", "sector": "Food", "country": "Ghana", "goal": "Find buyers"}


@pytest.fixture
def setup(tmp_path):
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="sqlite+pysqlite:///" + (tmp_path / "business.db").as_posix(),
        google_client_id="sample",
        google_client_secret="dummy",
        oauth_session_secret="dummy",
    )
    api = create_app(settings)
    engine = api.state.database_engine
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [User(id="alice", email="a@example.invalid"), User(id="bob", email="b@example.invalid")]
        )
        db.flush()
        tokens = {user: create_session(db, user) for user in ("alice", "bob")}
        db.commit()
    with TestClient(api) as client:
        yield client, engine, tokens, settings.session_cookie_name
    engine.dispose()


def login(setup, user="alice"):
    client, _, tokens, cookie = setup
    client.cookies.set(cookie, tokens[user])
    return client


def counts(engine):
    with Session(engine) as db:
        return [
            db.scalar(select(func.count()).select_from(model))
            for model in (Organization, Membership, BusinessProfile)
        ]


def test_auth_required_and_identity_headers_ignored(setup):
    client, engine, _, _ = setup
    assert (
        client.post(
            "/api/businesses", json=INPUT, headers={**ORIGIN, "X-User-ID": "alice"}
        ).status_code
        == 401
    )
    assert client.get("/api/businesses").status_code == 401
    assert counts(engine) == [0, 0, 0]


def test_registration_is_atomic_owned_persistent_and_listed(setup):
    client = login(setup)
    result = client.post(
        "/api/businesses", json={**INPUT, "name": " Sample Cocoa "}, headers=ORIGIN
    )
    assert result.status_code == 201
    business = result.json()
    assert business["name"] == "Sample Cocoa" and business["role"] == "owner"
    assert counts(setup[1]) == [1, 1, 1]
    with Session(setup[1]) as db:
        assert db.get(Membership, ("alice", business["organization_id"])).role == "owner"
    response = client.get("/api/businesses")
    assert response.json() == {"businesses": [business]}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "patch",
    [
        {"name": " "},
        {"sector": ""},
        {"country": "x" * 81},
        {"goal": "x" * 501},
        {"user_id": "bob"},
        {"organization_id": "other"},
        {"role": "owner"},
    ],
)
def test_invalid_or_forged_fields_rejected(setup, patch):
    assert (
        login(setup).post("/api/businesses", json={**INPUT, **patch}, headers=ORIGIN).status_code
        == 422
    )
    assert counts(setup[1]) == [0, 0, 0]


@pytest.mark.parametrize("origin", [None, "null", "https://untrusted.invalid"])
def test_csrf_rejected(setup, origin):
    headers = {} if origin is None else {"Origin": origin}
    assert login(setup).post("/api/businesses", json=INPUT, headers=headers).status_code == 403
    assert counts(setup[1]) == [0, 0, 0]


def test_form_posts_rejected(setup):
    assert login(setup).post("/api/businesses", data=INPUT, headers=ORIGIN).status_code == 415


def test_tenant_isolation_and_session_revocation(setup):
    client = login(setup)
    assert client.post("/api/businesses", json=INPUT, headers=ORIGIN).status_code == 201
    client = login(setup, "bob")
    assert client.get("/api/businesses", params={"user_id": "alice"}).json() == {"businesses": []}
    assert client.get("/api/auth/me").json()["id"] == "bob"
    with Session(setup[1]) as db:
        revoke_session(db, setup[2]["bob"])
        db.commit()
    assert client.get("/api/businesses").status_code == 401


@pytest.mark.parametrize("failure", ["insert", "commit"])
def test_database_failure_rolls_back_every_record(setup, monkeypatch, failure):
    def fail(*args, **kwargs):
        raise IntegrityError("private detail", {}, Exception("private detail"))

    if failure == "insert":
        monkeypatch.setattr(
            repository, "create_business", lambda db, user, data: partial_insert(db, fail)
        )
    else:
        event.listen(setup[1], "commit", fail)
    response = login(setup).post("/api/businesses", json=INPUT, headers=ORIGIN)
    assert response.status_code == 503 and "private detail" not in response.text
    if failure == "commit":
        event.remove(setup[1], "commit", fail)
    assert counts(setup[1]) == [0, 0, 0]


def partial_insert(db, fail):
    db.add(Organization(name="Should roll back"))
    db.flush()
    fail()


def test_duplicate_retry_and_multiple_businesses(setup):
    client = login(setup)
    first = client.post("/api/businesses", json=INPUT, headers=ORIGIN)
    retry = client.post("/api/businesses", json=INPUT, headers=ORIGIN)
    assert retry.status_code == 200 and retry.json() == first.json()
    assert (
        client.post(
            "/api/businesses", json={**INPUT, "name": "Second business"}, headers=ORIGIN
        ).status_code
        == 201
    )
    assert len(client.get("/api/businesses").json()["businesses"]) == 2


def test_concurrent_duplicate_registration(setup):
    def register(_):
        with Session(setup[1]) as db:
            return register_business(db, "alice", BusinessRegistration(**INPUT))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(register, range(2)))
    assert sorted(created for _, created in results) == [False, True]
    assert results[0][0].organization_id == results[1][0].organization_id
    assert counts(setup[1]) == [1, 1, 1]
