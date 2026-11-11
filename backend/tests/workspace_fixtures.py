import pytest
from test_business import INPUT, ORIGIN, login
from test_business import setup as setup


@pytest.fixture
def businesses(setup):
    client = login(setup)
    a = client.post("/api/businesses", json=INPUT, headers=ORIGIN).json()["organization_id"]
    b = client.post("/api/businesses", json={**INPUT, "name": "Second"}, headers=ORIGIN).json()[
        "organization_id"
    ]
    return a, b


def path(business, suffix=""):
    return f"/api/businesses/{business}" + suffix
