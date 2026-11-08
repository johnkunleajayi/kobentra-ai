"""Server-side, single-use OAuth transactions."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from .models import OAuthTransaction


class InvalidOAuthTransaction(Exception):
    """OAuth state is invalid, expired, or already consumed."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def state_digest(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def create_transaction(
    db: Session,
    lifetime_minutes: int = 10,
) -> tuple[str, str, str]:
    """Create an OAuth transaction.

    Returns state, nonce, and PKCE verifier.
    Caller must commit before redirecting to Google.
    """

    if not 1 <= lifetime_minutes <= 10:
        raise ValueError("Invalid OAuth transaction lifetime")

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(48)

    now = utc_now()

    db.add(
        OAuthTransaction(
            state_hash=state_digest(state),
            nonce=nonce,
            code_verifier=verifier,
            created_at=now,
            expires_at=now + timedelta(minutes=lifetime_minutes),
        )
    )

    db.flush()

    return state, nonce, verifier


def consume_transaction(
    db: Session,
    state: str,
) -> OAuthTransaction:
    """Atomically consume an OAuth transaction.

    Only one concurrent request can successfully consume a state.
    Caller must commit the transaction.
    """

    if not isinstance(state, str) or not 1 <= len(state) <= 256:
        raise InvalidOAuthTransaction()

    now = utc_now()

    statement = (
        update(OAuthTransaction)
        .where(
            OAuthTransaction.state_hash == state_digest(state),
            OAuthTransaction.consumed_at.is_(None),
            OAuthTransaction.expires_at > now,
        )
        .values(consumed_at=now)
        .returning(OAuthTransaction)
    )

    record = db.execute(statement).scalar_one_or_none()

    if record is None:
        raise InvalidOAuthTransaction()

    return record
