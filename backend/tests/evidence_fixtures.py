from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session
from test_business import login
from workspace_fixtures import businesses as businesses
from workspace_fixtures import setup as setup

from app.assessments.models import BusinessAssessment
from app.qualification.provider import MAPPING, P

TEXTS = [
    "What is your registered business name?",
    "In which country is your business primarily based?",
    "What industry does your business primarily operate in?",
    "What types of business partnerships are you currently seeking?",
    "Which West African markets can your business currently serve?",
    "How many years has your business been operating?",
    "What is your business's current operational capacity?",
    "Has your business previously engaged in partnerships or commercial transactions with businesses in other countries?",
    "How soon is your business ready to begin a new partnership?",
    "What are your business's key capabilities, and what makes your organization a suitable partner for other businesses?",
]
PARENT = "a0V000000000001AAA"
LEAD = "00Q000000000001AAA"


class Source:
    origin = "https://sample.my.salesforce.com"

    def __init__(self, settings, stamp):
        self.settings, self.stamp = settings, stamp
        self.rows, self.links, self.choices, self.questions, self.queries = [], [], [], [], []
        for i, (qid, spec) in enumerate(MAPPING["questions"].items()):
            result = f"a0P{i:012d}AAA"
            self.questions.append(
                {
                    "Id": qid,
                    P + "Survey__c": MAPPING["survey_id"],
                    P + "Type__c": spec["type"],
                    P + "Question_Plain_Text__c": TEXTS[i],
                }
            )
            row = {
                "Id": result,
                P + "Survey_Result__c": PARENT,
                P + "Question__c": qid,
                P + "Answered__c": True,
                P + "Answer_Text__c": f"Sample display {i}",
                P + "Answer_Value__c": None,
                P + "Answer_Number__c": None,
                P + "Answer_Polar__c": None,
                P + "Question_Display_Order__c": f"000 {i + 1:03d}",
            }
            if spec["type"] == "Number":
                row[P + "Answer_Number__c"] = 4
            elif spec["type"] not in {"Text-Short", "Text-Long"}:
                for n in range(2 if spec["type"] == "Multiple Choice" else 1):
                    cid = f"a00{i * 10 + n:012d}AAA"
                    value = "True" if spec["type"] == "Polar-Yes/No" else f"stored-{i}-{n}"
                    self.choices.append(
                        {
                            "Id": cid,
                            P + "Question__c": qid,
                            P + "Choice_Label__c": f"Label {i} {n}",
                            P + "Choice_Value__c": value,
                        }
                    )
                    self.links.append(
                        {
                            "Id": f"a01{i * 10 + n:012d}AAA",
                            P + "Question_Result__c": result,
                            P + "Ans_Choice__c": cid,
                            P + "Selected_Order__c": n,
                        }
                    )
                row[P + "Answer_Value__c"] = "separate stored representation"
                if spec["type"] == "Polar-Yes/No":
                    row[P + "Answer_Polar__c"] = "True"
            self.rows.append(row)

    def request(self, method, path):
        assert method == "GET"
        if path.endswith("/" + PARENT):
            return {
                "Id": PARENT,
                P + "Target_Lead__c": LEAD,
                "StatusField__c": "Completed",
                "SurveyField__c": MAPPING["survey_id"],
                P + "Response_End_Time__c": self.stamp.isoformat(),
            }
        if path.endswith("/ArdiraSurvey__Survey_Result__c/describe"):
            return {
                "fields": [
                    {
                        "name": "StatusField__c",
                        "picklistValues": [{"active": True, "value": "Completed"}],
                    },
                    {"name": "SurveyField__c", "referenceTo": ["Survey__c"]},
                ]
            }
        assert path.endswith("/Survey__c/describe")
        return {"keyPrefix": "a0Z"}

    def query(self, soql):
        self.queries.append(soql)
        if "FROM ArdiraSurvey__Question_Result__c " in soql:
            assert f"WHERE {P}Survey_Result__c = '{PARENT}'" in soql
            return self.rows
        if "FROM ArdiraSurvey__Question_Result_Choice__c " in soql:
            return self.links
        if "FROM ArdiraSurvey__Answer_Choice__c " in soql:
            return self.choices
        return self.questions

    def close(self):
        pass


@pytest.fixture
def evidence(setup, businesses):
    stamp = datetime.now(timezone.utc)
    source = Source(setup[0].app.state.settings, stamp)
    setup[0].app.state.salesforce_client = source
    with Session(setup[1]) as db:
        row = BusinessAssessment(
            organization_id=businesses[0],
            business_id=businesses[0],
            provider_survey_id=MAPPING["survey_id"],
            provider_logical_id="salesforce_flow",
            assessment_type="partner_qualification",
            initiated_by="alice",
            status="completed_verified",
            integration_mode="salesforce_flow",
            salesforce_lead_id=LEAD,
            provider_response_id=PARENT,
            completed_at=stamp,
            synchronized_at=stamp,
            dispatch_payload={"instance": source.origin},
        )
        db.add(row)
        db.flush()
        assessment_id = row.id
        db.commit()
    client = login(setup)
    return (
        client,
        f"/api/businesses/{businesses[0]}/assessments/{assessment_id}",
        source,
        assessment_id,
    )
