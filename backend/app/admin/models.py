"""Administrative decisions are separate from self-reported profile/evidence."""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..models import Base, uid


class BusinessAdministration(Base):
    __tablename__ = "business_administration"
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    approval: Mapped[str] = mapped_column(String(12), default="pending", server_default="pending")
    identity: Mapped[str] = mapped_column(
        String(12), default="unverified", server_default="unverified"
    )
    access: Mapped[str] = mapped_column(String(12), default="active", server_default="active")
    version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    __table_args__ = (
        CheckConstraint("approval IN ('pending','approved','rejected')", name="admin_approval"),
        CheckConstraint("identity IN ('unverified','verified')", name="admin_identity"),
        CheckConstraint("access IN ('active','suspended')", name="admin_access"),
        CheckConstraint("version >= 0", name="admin_version"),
    )


class AdministrativeDecision(Base):
    __tablename__ = "administrative_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(Text)
    evidence_references: Mapped[list] = mapped_column(JSON)
    previous_values: Mapped[dict] = mapped_column(JSON)
    new_values: Mapped[dict] = mapped_column(JSON)
    request_id: Mapped[str] = mapped_column(String(36))
    payload_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    __table_args__ = (UniqueConstraint("organization_id", "request_id", name="uq_admin_request"),)


@event.listens_for(AdministrativeDecision, "before_update")
@event.listens_for(AdministrativeDecision, "before_delete")
def immutable_decision(mapper, connection, target):
    raise ValueError("Administrative decisions are append-only")
