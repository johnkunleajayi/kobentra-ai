from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..schemas import ProfileInput


class DecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: UUID
    expected_version: int = Field(ge=0, strict=True)
    reason: str = Field(min_length=1, max_length=2000)


class StatusDecision(DecisionInput):
    action: Literal[
        "approve", "reject", "verify_identity", "revoke_identity", "suspend", "reactivate"
    ]
    evidence_references: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def evidence_required(self):
        if any(not ref.strip() or len(ref) > 500 for ref in self.evidence_references):
            raise ValueError("Invalid evidence reference")
        if self.action == "verify_identity" and not self.evidence_references:
            raise ValueError("Independent identity evidence references are required")
        return self


class ProfileDecision(DecisionInput):
    profile: ProfileInput
