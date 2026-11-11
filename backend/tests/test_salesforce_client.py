import httpx
import pytest
from pydantic import SecretStr

from app.config import Settings
from app.salesforce.client import SalesforceClient, SalesforceError


def test_token_cache_expiry_and_one_401_renewal():
    state = {"tokens": 0, "calls": 0}

    def respond(request):
        if request.url.path.endswith("/token"):
            state["tokens"] += 1
            return httpx.Response(200, json={"access_token": "dummy", "expires_in": 60})
        state["calls"] += 1
        return httpx.Response(401 if state["calls"] == 1 else 200, json={})

    settings = Settings(
        _env_file=None,
        salesforce_instance_url="https://sample.my.salesforce.com",
        salesforce_client_id=SecretStr("dummy"),
        salesforce_client_secret=SecretStr("dummy"),
    )
    client = SalesforceClient(settings, transport=httpx.MockTransport(respond))
    client.request("GET", "/services/data/v68.0/limits")
    assert state == {"tokens": 2, "calls": 2}
    client.request("GET", "/services/data/v68.0/limits")
    assert state["tokens"] == 2
    client.expires = 0
    client.request("GET", "/services/data/v68.0/limits")
    assert state["tokens"] == 3
    client.close()


def test_salesforce_error_is_safe_and_not_retried():
    def respond(request):
        return httpx.Response(500, text="secret-provider-payload")

    settings = Settings(
        _env_file=None,
        salesforce_instance_url="https://sample.my.salesforce.com",
        salesforce_client_id="dummy",
        salesforce_client_secret="dummy",
    )
    client = SalesforceClient(settings, transport=httpx.MockTransport(respond))
    with pytest.raises(SalesforceError) as exc:
        client.request("GET", "/services/data/v68.0/limits")
    assert "secret-provider-payload" not in str(exc.value)
    client.close()
