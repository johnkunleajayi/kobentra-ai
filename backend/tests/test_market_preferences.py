from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_business import ORIGIN, login
from workspace_fixtures import businesses as businesses
from workspace_fixtures import path
from workspace_fixtures import setup as setup

from app.market_preferences.schemas import PreferencesInput
from app.market_preferences.service import save
from app.security import Principal


def test_preferences_save_replace_repeat_and_isolation(setup, businesses):
    client = login(setup)
    a, b = businesses
    payload = {"preferences": [{"country": " Ghana ", "partner_type": " Distributor "}]}
    result = client.put(path(a, "/market-preferences"), json=payload, headers=ORIGIN)
    assert result.status_code == 200
    assert result.json()["preferences"] == [{"country": "Ghana", "partner_type": "Distributor"}]
    assert (
        client.put(path(a, "/market-preferences"), json=payload, headers=ORIGIN).json()
        == result.json()
    )
    assert client.get(path(a, "/market-preferences")).json() == result.json()
    assert client.get(path(b, "/market-preferences")).json() == {"preferences": []}
    assert client.put(
        path(a, "/market-preferences"), json={"preferences": []}, headers=ORIGIN
    ).json() == {"preferences": []}


@pytest.mark.parametrize(
    "payload",
    [
        {"preferences": [{"country": " ", "partner_type": "Buyer"}]},
        {"preferences": [{"country": "Ghana", "partner_type": "x" * 41}]},
        {"preferences": [{"country": "Ghana", "partner_type": "Buyer"}] * 2},
        {"preferences": [], "organization_id": "other"},
        {"preferences": [{"country": "x" * 81, "partner_type": "Buyer"}]},
    ],
)
def test_invalid_preferences(setup, businesses, payload):
    assert (
        login(setup)
        .put(path(businesses[0], "/market-preferences"), json=payload, headers=ORIGIN)
        .status_code
        == 422
    )


def test_preference_failure_preserves_previous_values(setup, businesses):
    client = login(setup)
    url = path(businesses[0], "/market-preferences")
    old = {"preferences": [{"country": "Ghana", "partner_type": "Buyer"}]}
    client.put(url, json=old, headers=ORIGIN)

    def fail(*args):
        raise IntegrityError("private detail", {}, Exception("private detail"))

    event.listen(setup[1], "commit", fail)
    try:
        response = client.put(url, json={"preferences": []}, headers=ORIGIN)
        assert response.status_code == 503 and "private detail" not in response.text
    finally:
        event.remove(setup[1], "commit", fail)
    assert client.get(url).json() == old


def test_concurrent_preferences_are_atomic(setup, businesses):
    def write(country):
        with Session(setup[1]) as db:
            save(
                db,
                Principal("alice"),
                businesses[0],
                PreferencesInput(preferences=[{"country": country, "partner_type": "Buyer"}]),
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(write, ["Ghana", "Senegal"]))
    rows = login(setup).get(path(businesses[0], "/market-preferences")).json()["preferences"]
    assert len(rows) == 1 and rows[0]["country"] in {"Ghana", "Senegal"}
