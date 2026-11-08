"""Persistent, opaque authentication sessions."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AuthSession


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(
    db: Session,
    user_id: str,
    lifetime_hours: int = 24,
) -> str:
    """Create a session and return its raw browser token.

    The raw token is never persisted in the database.
    The caller must commit the transaction before issuing a cookie.
    """
    if not 1 <= lifetime_hours <= 720:
        raise ValueError("Invalid session lifetime")

    token = secrets.token_urlsafe(48)
    now = utc_now()

    db.add(
        AuthSession(
            user_id=user_id,
            token_hash=token_digest(token),
            created_at=now,
            expires_at=now + timedelta(hours=lifetime_hours),
        )
    )

    db.flush()
    return token


def get_active_session(db: Session, token: str | None) -> AuthSession | None:
    """Return an active session for a valid opaque token."""
    if not token or len(token) > 256:
        return None

    now = utc_now()

    record = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == token_digest(token),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
    )

    return record


def revoke_session(db: Session, token: str | None) -> bool:
    """Revoke an active session; caller commits the transaction."""
    record = get_active_session(db, token)

    if record is None:
        return False

    record.revoked_at = utc_now()
    db.flush()

    return True
