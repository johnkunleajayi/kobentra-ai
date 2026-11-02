import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.integrations import DisconnectedSalesforce, IntegrationScope, PlannedEventSpark
from app.main import create_app
from app.models import (
    Base,
    BusinessEvent,
    BusinessProfile,
    IntroductionRequest,
    MarketPreference,
    MatchExplanation,
    Membership,
    Opportunity,
    Organization,
    User,
)
from app.schemas import IntroductionInput, ProfileInput
from app.security import Principal, authorize, scoped_get, scoped_list


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def fk(dbapi, record):
        dbapi.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                User(id="alice", email="alice@example.invalid"),
                User(id="bob", email="bob@example.invalid"),
                User(id="member", email="member@example.invalid"),
                Organization(id="a", name="Fictional A"),
                Organization(id="b", name="Fictional B"),
            ]
        )
        session.flush()
        session.add_all(
            [
                Membership(user_id="alice", organization_id="a", role="owner"),
                Membership(user_id="bob", organization_id="b", role="admin"),
                Membership(user_id="member", organization_id="a", role="member"),
            ]
        )
        session.flush()
        for tenant in ["a", "b"]:
            session.add_all(
                [
                    Opportunity(id=f"opp-{tenant}", organization_id=tenant, title="Sample"),
                    BusinessProfile(
                        id=f"profile-{tenant}",
                        organization_id=tenant,
                        name="Sample",
                        sector="Trade",
                        country="Ghana",
                        goal="Sample goal",
                    ),
                    MarketPreference(
                        id=f"pref-{tenant}",
                        organization_id=tenant,
                        country="Ghana",
                        partner_type="buyer",
                    ),
                    BusinessEvent(
                        id=f"event-{tenant}",
                        organization_id=tenant,
                        title="Sample event",
                        country="Ghana",
                    ),
                ]
            )
            session.flush()
            session.add_all(
                [
                    MatchExplanation(
                        id=f"match-{tenant}",
                        organization_id=tenant,
                        opportunity_id=f"opp-{tenant}",
                        explanation="Sample",
                        provenance="fixture",
                    ),
                    IntroductionRequest(
                        id=f"intro-{tenant}",
                        organization_id=tenant,
                        opportunity_id=f"opp-{tenant}",
                        message="Sample request",
                    ),
                ]
            )
        session.commit()
        yield session
    engine.dispose()


@pytest.mark.parametrize(
    "model",
    [
        Opportunity,
        BusinessProfile,
        MarketPreference,
        MatchExplanation,
        IntroductionRequest,
        BusinessEvent,
    ],
)
def test_every_tenant_resource_is_scoped(db, model):
    rows = scoped_list(db, model, Principal("alice"), "a")
    assert len(rows) == 1 and rows[0].organization_id == "a"
    with pytest.raises(HTTPException) as exc:
        scoped_list(db, model, Principal("alice"), "b")
    assert exc.value.status_code == 403
    foreign = db.query(model).filter_by(organization_id="b").one()
    with pytest.raises(HTTPException) as exc:
        scoped_get(db, model, Principal("alice"), "a", foreign.id)
    assert exc.value.status_code == 404


@pytest.mark.parametrize("user", ["unknown", "bob"])
def test_nonmembers_denied(db, user):
    with pytest.raises(HTTPException):
        authorize(db, Principal(user), "a")


def test_member_write_denied(db):
    authorize(db, Principal("member"), "a")
    with pytest.raises(HTTPException):
        authorize(db, Principal("member"), "a", write=True)
    authorize(db, Principal("alice"), "a", write=True)


@pytest.mark.parametrize(
    "model,fields",
    [
        (MatchExplanation, {"explanation": "Sample", "provenance": "fixture"}),
        (IntroductionRequest, {"message": "Sample request"}),
    ],
)
def test_cross_tenant_relationship_rejected(db, model, fields):
    db.add(model(organization_id="a", opportunity_id="opp-b", **fields))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_health_and_fail_closed_auth():
    with TestClient(create_app(Settings(app_env="test"))) as client:
        response = client.get("/api/health")
        assert response.status_code == 200 and response.json()["salesforce"] == "not_connected"
        assert response.headers["x-request-id"]
        for headers in [
            {},
            {"X-User-ID": "alice", "X-Organization-ID": "a"},
            {"Authorization": "Bearer fabricated"},
        ]:
            response = client.get("/api/workspace", headers=headers)
            assert (
                response.status_code == 401
                and response.json()["error"]["code"] == "authentication_required"
            )


def test_cors_allowlist():
    with TestClient(create_app(Settings(app_env="test"))) as client:
        assert (
            client.get("/api/health", headers={"Origin": "http://127.0.0.1:5173"}).headers[
                "access-control-allow-origin"
            ]
            == "http://127.0.0.1:5173"
        )
        assert (
            "access-control-allow-origin"
            not in client.get(
                "/api/health", headers={"Origin": "https://untrusted.invalid"}
            ).headers
        )


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://example.invalid/db",
        "postgresql+psycopg://example.invalid/db",
        "https://example.invalid",
    ],
)
def test_remote_database_configuration_rejected(url):
    with pytest.raises(ValidationError):
        Settings(database_url=url)


@pytest.mark.parametrize(
    "origins",
    [
        ["*"],
        ["https://example.invalid/path"],
        ["https://user:pass@example.invalid"],
        [],
    ],
)
def test_invalid_origins_rejected(origins):
    with pytest.raises(ValidationError):
        Settings(cors_origins=origins)


@pytest.mark.parametrize(
    "change",
    [{"name": "   "}, {"goal": ""}, {"organization_id": "other"}, {"name": "x" * 101}],
)
def test_profile_validation(change):
    values = {
        "name": "Sample",
        "sector": "Trade",
        "country": "Ghana",
        "goal": "Find distributors",
    }
    values.update(change)
    with pytest.raises(ValidationError):
        ProfileInput(**values)


def test_intro_validation():
    with pytest.raises(ValidationError):
        IntroductionInput(opportunity_id="bad", message="short")


@pytest.mark.parametrize(
    "adapter,method",
    [
        (DisconnectedSalesforce(), "sync_authorized_opportunities"),
        (PlannedEventSpark(), "discover_authorized_events"),
    ],
)
def test_adapters_never_simulate_success(adapter, method):
    with pytest.raises(RuntimeError):
        getattr(adapter, method)(IntegrationScope("a", "alice"))


def test_postgresql_schema_compiles_without_connection():
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable

    sql = "\n".join(
        str(CreateTable(t).compile(dialect=postgresql.dialect()))
        for t in Base.metadata.sorted_tables
    )
    assert "FOREIGN KEY(opportunity_id, organization_id)" in sql
    assert "TIMESTAMP WITH TIME ZONE" in sql


def test_local_engine_enforces_foreign_keys():
    from sqlalchemy import text

    from app.database import local_engine

    engine = local_engine(Settings(database_url="sqlite+pysqlite:///:memory:"))
    with engine.connect() as connection:
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1
    engine.dispose()


def test_validation_response_does_not_echo_input():
    api = create_app(Settings(app_env="test"))

    @api.post("/test-validation")
    def validate(value: ProfileInput):
        return value

    with TestClient(api) as client:
        response = client.post("/test-validation", json={"private": "do-not-echo-this"})
        assert response.status_code == 422
        assert "do-not-echo-this" not in response.text
        assert response.json()["error"]["code"] == "validation_failed"
        assert client.get("/api/missing").json()["error"]["code"] == "not_found"
