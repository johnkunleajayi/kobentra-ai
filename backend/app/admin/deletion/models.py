from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from ...models import Base, uid
from ..models import immutable_decision


class DeletionOperation(Base):
    __tablename__ = "business_deletions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), unique=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(40))
    error_code: Mapped[str | None] = mapped_column(String(60))
    target: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(
            "state IN ('local_pending','salesforce_pending','salesforce_retry','awaiting_permanent_purge','completed')",
            name="deletion_state",
        ),
    )


class DeletionEvent(Base):
    __tablename__ = "business_deletion_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    operation_id: Mapped[str] = mapped_column(ForeignKey("business_deletions.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    state: Mapped[str] = mapped_column(String(40))
    error_code: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    __table_args__ = (UniqueConstraint("operation_id", "id", name="uq_deletion_event"),)


event.listen(DeletionEvent, "before_update", immutable_decision)
event.listen(DeletionEvent, "before_delete", immutable_decision)
