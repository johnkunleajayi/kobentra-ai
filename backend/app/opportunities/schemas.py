from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OpportunityInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=160)
    stage: Literal["exploring", "conversation", "closed"] = "exploring"


class OpportunitySummary(OpportunityInput):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str


class OpportunityList(BaseModel):
    opportunities: list[OpportunitySummary]
