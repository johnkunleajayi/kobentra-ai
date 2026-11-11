from copy import deepcopy

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session
from test_business import INPUT, ORIGIN, login
from workspace_fixtures import businesses as businesses
from workspace_fixtures import setup as setup

from app.config import Settings
from app.matching.engine import RULES, compare
from app.models import BusinessProfile, MarketPreference


def pair():
    return (
        {
            "sector": "Food",
            "country": "Nigeria",
            "preferences": [{"country": "Ghana", "partner_type": "Buyer"}],
        },
        {
            "sector": "Food",
            "country": "Ghana",
            "preferences": [{"country": "Nigeria", "partner_type": "Supplier"}],
        },
    )


def test_complementary_intent_geography_determinism_and_coverage():
    a, b = pair()
    original = deepcopy((a, b))
    result = compare(a, b)
    assert result == compare(a, b) == compare(b, a)
    assert (a, b) == original
    assert result["rules_version"] == "kobentra-matching-v1"
    assert result["score"] == 100 and result["coverage_percent"] == 62.5
    assert sum(RULES["weights"].values()) == 100
    assert result["dimensions"][3]["state"] == "unknown"
    assert result["dimensions"][4]["state"] == "unknown"


def test_geography_incompatible_and_unrecognized_intent_not_invented():
    a, b = pair()
    b["preferences"][0]["country"] = "Senegal"
    result = compare(a, b)
    assert result["dimensions"][2]["state"] == "incompatible"
    assert result["score"] is None
    b["preferences"][0]["partner_type"] = "Amazing partner"
    assert compare(a, b)["dimensions"][0]["state"] == "unknown"


def test_missing_conflicting_and_different_industry_are_unknown():
    a, b = pair()
    a["conflicts"] = ["intent"]
    assert compare(a, b)["score"] is None
    assert compare(a, b)["dimensions"][0]["state"] == "unknown"
    a["preferences"] = []
    b["sector"] = "Technology"
    result = compare(a, b)
    assert result["coverage_percent"] == 0 and result["score"] is None
    assert all(d["state"] == "unknown" for d in result["dimensions"])


def test_private_by_default_authenticated_discovery_and_projection(setup, businesses):
    client = login(setup)
    # A separate user's business: discovery does not grant membership or evidence access.
    login(setup, "bob")
    created = client.post(
        "/api/businesses", json={**INPUT, "name": "Partner", "country": "Nigeria"}, headers=ORIGIN
    )
    partner = created.json()["organization_id"]
    from app.admin.models import BusinessAdministration
    with Session(setup[1]) as db:
        db.add(BusinessAdministration(organization_id=partner, approval="approved"))
        db.add_all(
            [
                MarketPreference(
                    organization_id=businesses[0], country="Nigeria", partner_type="Buyer"
                ),
                MarketPreference(organization_id=partner, country="Ghana", partner_type="Supplier"),
            ]
        )
        db.commit()
    login(setup)
    path = f"/api/businesses/{businesses[0]}/matches"
    assert client.get(path).json()["matches"] == []
    setup[0].app.state.settings.matching_discovery_business_ids = [partner, businesses[0]]
    response = client.get(path)
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    body = response.json()
    assert len(body["matches"]) == 1
    match = body["matches"][0]
    assert set(match["partner"]) == {"business_id", "name", "sector", "country"}
    assert match["compatibility"]["score"] == 100
    assert match["introduction_eligibility"]["allowed"] is False
    assert match["introduction_eligibility"]["missing_verifications"] == ["business_identity"]
    assert "normalized_value" not in response.text and "question_result_id" not in response.text
    assert "goal" not in match["partner"] and "preferences" not in match["partner"]
    assert client.get(f"/api/businesses/{partner}").status_code == 403
    assert client.get(f"/api/businesses/{partner}/qualification").status_code == 403
    assert client.get(f"/api/businesses/{partner}/matches").status_code == 403
    setup[0].app.state.settings.matching_discovery_business_ids = []
    assert client.get(path).json()["matches"] == []
    client.cookies.clear()
    assert client.get(path).status_code == 401


def test_same_country_and_self_are_not_cross_border_matches(setup, businesses):
    client = login(setup)
    setup[0].app.state.settings.matching_discovery_business_ids = list(businesses)
    assert client.get(f"/api/businesses/{businesses[0]}/matches").json()["matches"] == []


def test_configuration_rejects_unbounded_or_invalid_directory():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, matching_discovery_business_ids=["*"])


def test_candidate_private_evidence_is_not_queried(setup, businesses):
    from sqlalchemy import event

    client = login(setup)
    with Session(setup[1]) as db:
        db.get(
            BusinessProfile,
            db.query(BusinessProfile).filter_by(organization_id=businesses[1]).one().id,
        ).country = "Nigeria"
        db.commit()
    queries = []

    def capture(conn, cursor, statement, parameters, context, many):
        if "assessment_evidence" in statement:
            queries.append(parameters)

    event.listen(setup[1], "before_cursor_execute", capture)
    try:
        setup[0].app.state.settings.matching_discovery_business_ids = [businesses[1]]
        assert client.get(f"/api/businesses/{businesses[0]}/matches").status_code == 200
    finally:
        event.remove(setup[1], "before_cursor_execute", capture)
    assert queries and all(businesses[1] not in p for p in queries)
