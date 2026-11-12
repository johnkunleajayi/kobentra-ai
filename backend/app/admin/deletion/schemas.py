from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DeleteConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: UUID
    expected_version: int = Field(ge=0, strict=True)
    business_name: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=2000)
    preview_token: str = Field(pattern=r"^[a-f0-9]{64}$")
