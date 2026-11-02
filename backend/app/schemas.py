from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    sector: str = Field(min_length=1, max_length=100)
    country: str = Field(min_length=1, max_length=80)
    goal: str = Field(min_length=1, max_length=500)


class IntroductionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    opportunity_id: UUID
    message: str = Field(min_length=10, max_length=1000)
