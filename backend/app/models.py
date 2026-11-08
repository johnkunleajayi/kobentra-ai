from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    # Identity provider subjects only; password authentication is not implemented.
    provider_subject: Mapped[str | None] = mapped_column(String(255), unique=True)


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100))


class Membership(Base):
    __tablename__ = "memberships"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(12))
    __table_args__ = (CheckConstraint("role IN ('owner','admin','member')", name="valid_role"),)


class TenantRow:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)


class BusinessProfile(TenantRow, Base):
    __tablename__ = "business_profiles"
    name: Mapped[str] = mapped_column(String(100))
    sector: Mapped[str] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(80))
    goal: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("organization_id"),)


class MarketPreference(TenantRow, Base):
    __tablename__ = "market_preferences"
    country: Mapped[str] = mapped_column(String(80))
    partner_type: Mapped[str] = mapped_column(String(40))
    __table_args__ = (UniqueConstraint("organization_id", "country", "partner_type"),)


class Opportunity(TenantRow, Base):
    __tablename__ = "opportunities"
    title: Mapped[str] = mapped_column(String(160))
    stage: Mapped[str] = mapped_column(String(32), default="exploring")
    __table_args__ = (
        UniqueConstraint("id", "organization_id"),
        CheckConstraint("stage IN ('exploring','conversation','closed')", name="valid_stage"),
    )


class MatchExplanation(TenantRow, Base):
    __tablename__ = "match_explanations"
    opportunity_id: Mapped[str] = mapped_column(String(36))
    explanation: Mapped[str] = mapped_column(Text)
    provenance: Mapped[str] = mapped_column(String(100))
    __table_args__ = (
        ForeignKeyConstraint(
            ["opportunity_id", "organization_id"],
            ["opportunities.id", "opportunities.organization_id"],
        ),
    )


class IntroductionRequest(TenantRow, Base):
    __tablename__ = "introduction_requests"
    opportunity_id: Mapped[str] = mapped_column(String(36))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="requested")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # No recipient contact fields or contact-release operations in Phase 1.
    __table_args__ = (
        ForeignKeyConstraint(
            ["opportunity_id", "organization_id"],
            ["opportunities.id", "opportunities.organization_id"],
        ),
        CheckConstraint("status IN ('requested','withdrawn')", name="valid_request_status"),
    )


class BusinessEvent(TenantRow, Base):
    __tablename__ = "business_events"
    title: Mapped[str] = mapped_column(String(160))
    country: Mapped[str] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(80), default="local")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=uid
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )



class OAuthTransaction(Base):
    """Temporary server-side Google OAuth transaction."""

    __tablename__ = "oauth_transactions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uid,
    )

    state_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )

    nonce: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    code_verifier: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )

    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
