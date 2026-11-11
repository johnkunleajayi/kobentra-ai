from pydantic import BaseModel

from ..schemas import ProfileInput


class BusinessRegistration(ProfileInput):
    """Reuse trimmed, bounded profile fields; identity/ownership fields are forbidden."""


class BusinessSummary(BaseModel):
    organization_id: str
    profile_id: str
    name: str
    sector: str
    country: str
    goal: str
    role: str


class BusinessList(BaseModel):
    businesses: list[BusinessSummary]
