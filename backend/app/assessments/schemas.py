from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DispatchAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    last_name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class InitiateAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assessment_type: Literal["partner_qualification"] = "partner_qualification"


class AssessmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    business_id: str
    provider: str
    assessment_type: str
    provider_survey_id: str
    provider_response_id: str | None
    status: Literal["initiated", "launch_requested", "completed_verified"]
    initiated_at: datetime
    completed_at: datetime | None
    synchronized_at: datetime | None
    integration_mode: str = "shared_public_link"
    salesforce_lead_id: str | None = None
    dispatch_state: str | None = None
    processing_status: Literal["waiting", "ready", "retry", "needs_review"] | None = None
    processing_message: str | None = None

    @field_validator("initiated_at", "completed_at", "synchronized_at")
    @classmethod
    def utc_timestamp(cls, value: datetime | None):
        # SQLite drops timezone information; application-written timestamps are UTC.
        if value is None:
            return None
        return (
            value.replace(tzinfo=timezone.utc)
            if value.tzinfo is None
            else value.astimezone(timezone.utc)
        )


class AssessmentList(BaseModel):
    assessments: list[AssessmentSummary]


class ProviderConfiguration(BaseModel):
    title: str
    provider: str = "SurveyVista"
    configured: bool
    synchronization: Literal["not_connected", "salesforce_flow"] = "not_connected"
    unique_tracking_link: bool = False


class AssessmentLaunch(BaseModel):
    assessment: AssessmentSummary
    launch_url: str
    unique_tracking_link: bool = False
