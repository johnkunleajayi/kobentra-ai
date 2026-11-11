import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_business import login
from test_business import setup as setup

from app.demo import discovery
from app.matching.service import matches
from app.models import BusinessProfile, Membership, Organization
from app.security import Principal


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://example.invalid/demo",
        "sqlite+pysqlite:///:memory:",
        "sqlite+pysqlite:///D:/kobentra-ai/backend/kobentra-local.db",
    ],
)
def test_remote_or_unisolated_database_refused(url):
    with pytest.raises(ValueError):
        discovery.local_database(url)


def test_publication_approval_required_before_any_connection():
    with pytest.raises(ValueError, match="approval"):
        discovery.prepare("not-a-database", "alice")


def test_repeatable_fictional_demo_uses_real_engine_and_isolation(setup, monkeypatch):
    client, engine, _, _ = setup
    url = engine.url.render_as_string(hide_password=False)
    monkeypatch.setattr(discovery, "DEMO_ROOT", Path(engine.url.database).parent)
    approved = discovery.prepare(url, "alice", True)
    assert discovery.prepare(url, "alice", True) == approved
    ids = approved["business_ids"]
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Organization)) == 2
        assert db.scalar(select(func.count()).select_from(Membership)) == 2
        assert all(
            p.name.startswith("Fictional Demo — ") for p in db.scalars(select(BusinessProfile))
        )
        body = matches(db, Principal("alice"), ids[0], ids)
        assert len(body["matches"]) == 1
        fit = body["matches"][0]["compatibility"]
        assert fit["score"] == 100 and fit["coverage_percent"] == 62.5
        assert fit["dimensions"][3]["state"] == "unknown"
        assert fit["dimensions"][4]["state"] == "unknown"
        assert body["matches"][0]["introduction_eligibility"]["allowed"] is False
        assert matches(db, Principal("alice"), ids[0], [])["matches"] == []
    login(setup, "bob")
    assert client.get(f"/api/businesses/{ids[0]}/matches").status_code == 403
    login(setup)
    setup[0].app.state.settings.matching_discovery_business_ids = ids
    response = client.get(f"/api/businesses/{ids[0]}/matches")
    assert response.status_code == 200
    assert "normalized_value" not in response.text and "provider_response_id" not in response.text
    # Fictional-only API artifact for frontend browser tests: scores come from the real engine.
    target = Path(__file__).resolve().parents[2] / "work" / "discovery-fixture.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(response.json()), encoding="utf-8")


def test_unknown_local_owner_cannot_create_or_publish(setup, monkeypatch):
    engine = setup[1]
    monkeypatch.setattr(discovery, "DEMO_ROOT", Path(engine.url.database).parent)
    with pytest.raises(HTTPException):
        discovery.prepare(engine.url.render_as_string(hide_password=False), "missing-user", True)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Organization)) == 0
