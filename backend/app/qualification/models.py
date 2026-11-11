from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..models import Base, TenantRow


class AssessmentEvidence(TenantRow, Base):
    __tablename__ = "assessment_evidence"
    assessment_id: Mapped[str] = mapped_column(String(36))
    provider_response_id: Mapped[str] = mapped_column(String(18))
    extraction_version: Mapped[str] = mapped_column(String(40))
    content_hash: Mapped[str] = mapped_column(String(64))
    evidence_kind: Mapped[str] = mapped_column(String(30), default="self_reported")
    answers: Mapped[list] = mapped_column(JSON)
    gaps: Mapped[list] = mapped_column(JSON)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["assessment_id", "organization_id"],
            ["business_assessments.id", "business_assessments.organization_id"],
        ),
        UniqueConstraint(
            "assessment_id", "extraction_version", name="uq_assessment_evidence_version"
        ),
        CheckConstraint("evidence_kind = 'self_reported'", name="assessment_evidence_kind"),
    )
