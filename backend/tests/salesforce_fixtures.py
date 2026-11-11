import httpx
import pytest
from pydantic import SecretStr
from test_business import ORIGIN, login
from workspace_fixtures import businesses as businesses
from workspace_fixtures import setup as setup

from app.salesforce.client import SalesforceClient

LEAD = "00Q000000000001AAA"
RESULT = "a0R000000000001AAA"
ORIGIN_URL = "https://sample.my.salesforce.com"


@pytest.fixture
def native(setup, businesses):
    api = setup[0].app
    settings = api.state.settings
    settings.salesforce_dispatch_enabled = True
    settings.salesforce_instance_url = ORIGIN_URL
    settings.salesforce_client_id = SecretStr("dummy-client")
    settings.salesforce_client_secret = SecretStr("dummy-secret")
    state = {"tokens": 0, "posts": 0, "leads": [], "results": [], "fail": False}

    def respond(request):
        import json

        if request.url.path == "/services/oauth2/token":
            state["tokens"] += 1
            return httpx.Response(
                200,
                json={"access_token": "dummy-token", "expires_in": 60, "instance_url": ORIGIN_URL},
            )
        if request.method == "POST":
            state["posts"] += 1
            lead = {"Id": LEAD, **json.loads(request.content)}
            state["leads"].append(lead)
            if state.get("fail_status"):
                return httpx.Response(500, text="private-provider-error")
            if state["fail"]:
                raise httpx.ReadTimeout("ambiguous", request=request)
            return httpx.Response(201, json={"id": LEAD, "success": True})
        if request.url.path.endswith("/Lead/" + LEAD):
            return httpx.Response(200, json=state["leads"][0])
        if request.url.path.endswith("/ArdiraSurvey__Survey_Result__c/describe"):
            return httpx.Response(
                200,
                json={
                    "fields": [
                        {
                            "name": "VerifiedStatus__c",
                            "picklistValues": [{"value": "Completed", "active": True}],
                        },
                        {"name": "VerifiedSurvey__c", "referenceTo": ["ActualSurvey__c"]},
                    ]
                },
            )
        if request.url.path.endswith("/ActualSurvey__c/describe"):
            return httpx.Response(200, json={"keyPrefix": "a0Z"})
        rows = (
            state["results"]
            if "ArdiraSurvey__Survey_Result__c" in request.url.params.get("q", "")
            else state["leads"]
        )
        return httpx.Response(200, json={"records": rows, "done": True})

    api.state.salesforce_client = SalesforceClient(settings, transport=httpx.MockTransport(respond))
    client = login(setup)
    base = f"/api/businesses/{businesses[0]}/assessments"
    record = client.post(base, json={}, headers=ORIGIN).json()
    yield client, base + "/" + record["id"], state, api.state.salesforce_client
    api.state.salesforce_client.close()
