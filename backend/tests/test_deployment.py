"""Offline deployment contracts: no provider calls or remote database connections."""

import json
from pathlib import Path
from unittest.mock import Mock

import httpx
import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool
from test_business import login
from test_mvp import seed
from workspace_fixtures import businesses as businesses
from workspace_fixtures import setup as setup

from app.config import Settings
from app.database import database_engine
from app.main import create_app
from app.salesforce.budget import deadline, request_budget, timeout
from app.salesforce.client import SalesforceClient, SalesforceError

FRONT = "https://frontend.example.invalid"
PG = "postgresql://sample:dummy@neon.example.invalid/sample"


def production(**overrides):
    values = dict(
        app_env="production",
        vercel=True,
        database_url=PG,
        frontend_url=FRONT,
        cors_origins=[FRONT],
        google_redirect_uri=FRONT + "/api/auth/google/callback",
        google_client_id="dummy",
        google_client_secret="dummy",
        oauth_session_secret="x" * 32,
    )
    return Settings(_env_file=None, **(values | overrides))


@pytest.mark.parametrize(
    "changes",
    [
        {"app_env": "development"},
        {"database_url": "sqlite+pysqlite:///:memory:"},
        {"frontend_url": "http://frontend.example.invalid"},
        {"google_redirect_uri": "https://backend.example.invalid/api/auth/google/callback"},
        {"cors_origins": [FRONT, "http://localhost:5173"]},
        {"google_client_secret": None},
        {"oauth_session_secret": "weak"},
        {"salesforce_dispatch_enabled": True},
    ],
)
def test_public_configuration_fails_closed(changes):
    with pytest.raises(ValidationError):
        production(**changes)


def test_neon_engine_is_lazy_bounded_and_does_not_hold_instance_pool(monkeypatch):
    connect = Mock(side_effect=AssertionError("Remote access forbidden"))
    monkeypatch.setattr(psycopg, "connect", connect)
    engine = database_engine(production())
    assert isinstance(engine.pool, NullPool)
    args = engine.dialect.create_connect_args(engine.url)[1]
    assert args["sslmode"] == "verify-full" and args["channel_binding"] == "require"
    connection = Mock()
    engine.dispatch.begin(connection)
    assert connection.exec_driver_sql.call_count == 2
    connect.assert_not_called()
    engine.dispose()


def test_https_google_binding_and_cors_use_public_origin(setup):
    # Substitute only an isolated test engine; never connect the production URL.
    api = create_app(production())
    api.state.database_engine = setup[1]
    with TestClient(api, base_url=FRONT) as client:
        login = client.get("/api/auth/google/login", follow_redirects=False)
        assert login.status_code == 302
        assert "Secure" in login.headers["set-cookie"]
        assert "HttpOnly" in login.headers["set-cookie"]
        assert "SameSite=lax" in login.headers["set-cookie"]
        allowed = client.options(
            "/api/businesses", headers={"Origin": FRONT, "Access-Control-Request-Method": "POST"}
        )
        assert allowed.headers["access-control-allow-origin"] == FRONT
        denied = client.options(
            "/api/businesses",
            headers={"Origin": "https://evil.invalid", "Access-Control-Request-Method": "POST"},
        )
        assert denied.status_code == 400
        assert "no-store" in login.headers["cache-control"]
    api.state.database_engine.dispose()


def test_salesforce_budget_expires_without_replaying_requests():
    settings = Settings(
        _env_file=None,
        salesforce_instance_url="https://sample.my.salesforce.com",
        salesforce_client_id="dummy",
        salesforce_client_secret="dummy",
    )
    calls = []

    def respond(request):
        calls.append(request.method)
        return httpx.Response(
            200, json={"access_token": "dummy"} if request.url.path.endswith("/token") else {}
        )

    client = SalesforceClient(settings, transport=httpx.MockTransport(respond))
    with request_budget(True):
        assert timeout().read <= 15
        deadline.set(0)
        with pytest.raises(SalesforceError):
            client.request("GET", "/services/data/v68.0/limits")
    assert calls == [] and deadline.get() is None
    client.close()


def test_vercel_routing_and_evidence_assets_are_explicit():
    root = Path(__file__).resolve().parents[2]
    front = json.loads((root / "frontend/vercel.json").read_text())
    back = json.loads((root / "backend/vercel.json").read_text())
    assert front["rewrites"][0]["source"] == "/api/:path*"
    assert front["rewrites"][0]["destination"].endswith("/api/:path*")
    assert "api" in front["rewrites"][1]["source"]  # API misses must never become index.html.
    assert back["functions"]["app/main.py"]["maxDuration"] == 300
    assert "matching" in back["functions"]["app/main.py"]["includeFiles"]


@pytest.mark.parametrize("countries", [("Senegal", "Benin"), ("Togo", "Côte d’Ivoire")])
def test_discovery_is_country_generic_and_not_allowlist_dependent(setup, businesses, countries):
    from app.models import MarketPreference

    with Session(setup[1]) as db:
        for i, business in enumerate(businesses):
            seed(
                db,
                business,
                countries[i],
                "Food",
                "Distributors or resellers" if i == 0 else "Suppliers or manufacturers",
                "alice",
            )
            pref = db.scalar(
                select(MarketPreference).where(MarketPreference.organization_id == business)
            )
            pref.country = countries[1 - i]
        db.commit()
    client = login(setup)
    for i, business in enumerate(businesses):
        data = client.get(f"/api/businesses/{business}/matches").json()
        assert data["directory_status"] == "automatic" and data["discovery_eligible"]
        assert data["matches"][0]["partner"]["country"] == countries[1 - i]
        assert data["matches"][0]["compatibility"]["score"] is not None
