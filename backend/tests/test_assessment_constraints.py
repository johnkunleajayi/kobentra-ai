from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from workspace_fixtures import businesses as businesses
from workspace_fixtures import setup as setup

from app.assessments.models import BusinessAssessment
from app.config import Settings


@pytest.mark.parametrize(
    "changes",
    [
        {"business_id": "missing"},
        {"business_id": "other"},
        {"status": "completed_verified"},
        {"provider_response_id": "forged"},
        {"status": "completed"},
        {"provider": "other"},
    ],
)
def test_database_integrity_and_completion_evidence(setup, businesses, changes):
    values = dict(
        organization_id=businesses[0],
        business_id=businesses[0],
        initiated_by="alice",
        assessment_type="partner_qualification",
        provider_survey_id="sample",
        provider_logical_id="sample",
    )
    values.update(changes)
    if changes.get("business_id") == "other":
        values["business_id"] = businesses[1]
    with Session(setup[1]) as db:
        db.add(BusinessAssessment(**values))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_same_provider_response_cannot_be_bound_to_two_tenants(setup, businesses):
    now = datetime.now(timezone.utc)
    with Session(setup[1]) as db:
        for business in businesses:
            db.add(
                BusinessAssessment(
                    organization_id=business,
                    business_id=business,
                    initiated_by="alice",
                    assessment_type="partner_qualification",
                    provider_survey_id="sample",
                    provider_logical_id="sample",
                    provider_response_id="same-response",
                    status="completed_verified",
                    completed_at=now,
                    synchronized_at=now,
                )
            )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.invalid/?recordId=1&logicalId=2",
        "javascript:alert(1)",
        "https://orgfarm-7cee962a58-dev-ed.develop.my.site.com/kobentraassess/s/survey-response?recordId=1&logicalId=2&targetId=unverified",
    ],
)
def test_unexpected_launch_url_rejected(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, surveyvista_launch_url=url)
