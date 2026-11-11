from datetime import datetime, timezone

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..models import Base, TenantRow


class BusinessAssessment(TenantRow, Base):
    __tablename__ = "business_assessments"
    # The existing workspace business ID is its organization ID; one profile per org.
    business_id: Mapped[str] = mapped_column(ForeignKey("business_profiles.organization_id"))
    provider: Mapped[str] = mapped_column(String(30), default="surveyvista")
    assessment_type: Mapped[str] = mapped_column(String(60))
    provider_survey_id: Mapped[str] = mapped_column(String(100))
    provider_logical_id: Mapped[str] = mapped_column(String(100))
    provider_response_id: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="initiated")
    initiated_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    initiated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synchronized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    integration_mode: Mapped[str] = mapped_column(String(40), default="shared_public_link")
    salesforce_lead_id: Mapped[str | None] = mapped_column(String(18))
    correlation_id: Mapped[str | None] = mapped_column(String(36))
    dispatch_state: Mapped[str | None] = mapped_column(String(20))
    dispatch_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispatch_payload: Mapped[dict | None] = mapped_column(JSON)
    __table_args__ = (
        CheckConstraint("business_id = organization_id", name="assessment_business_tenant"),
        CheckConstraint("provider = 'surveyvista'", name="assessment_provider"),
        CheckConstraint(
            "integration_mode IN ('shared_public_link','salesforce_flow')",
            name="assessment_integration_mode",
        ),
        CheckConstraint(
            "dispatch_state IS NULL OR dispatch_state IN ('sending','uncertain','sent')",
            name="assessment_dispatch_state",
        ),
        UniqueConstraint("salesforce_lead_id", name="uq_assessment_lead"),
        UniqueConstraint("id", "organization_id", name="uq_assessment_id_org"),
        UniqueConstraint("correlation_id", name="uq_assessment_correlation"),
        CheckConstraint(
            "status IN ('initiated','launch_requested','completed_verified')",
            name="assessment_status",
        ),
        CheckConstraint(
            "(status IN ('initiated','launch_requested') AND provider_response_id IS NULL "
            "AND completed_at IS NULL AND synchronized_at IS NULL) OR "
            "(status = 'completed_verified' AND provider_response_id IS NOT NULL "
            "AND completed_at IS NOT NULL AND synchronized_at IS NOT NULL)",
            name="assessment_completion_evidence",
        ),
        UniqueConstraint(
            "provider", "provider_response_id", name="uq_assessment_provider_response"
        ),
    )
