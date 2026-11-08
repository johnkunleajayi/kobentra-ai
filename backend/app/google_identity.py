"""Provision users from verified Google OpenID Connect identities."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import User


class IdentityConflict(Exception):
    """An existing account cannot be linked automatically."""


class InvalidGoogleIdentity(Exception):
    """Required verified Google identity claims are missing."""


def resolve_google_user(
    db: Session,
    claims: dict,
) -> User:
    """Resolve or create a user using verified Google claims.

    The caller must verify Google's signed ID token before calling
    this function and commit the database transaction afterward.
    """

    subject = claims.get("sub")
    email = claims.get("email")
    verified = claims.get("email_verified")

    if not isinstance(subject, str) or not subject.strip():
        raise InvalidGoogleIdentity("Missing Google subject")

    if not isinstance(email, str) or not email.strip():
        raise InvalidGoogleIdentity("Missing Google email")

    if verified is not True:
        raise InvalidGoogleIdentity("Google email is not verified")

    subject = subject.strip()
    email = email.strip().lower()

    if len(subject) > 255 or len(email) > 254:
        raise InvalidGoogleIdentity("Invalid identity length")

    existing = db.scalar(
        select(User).where(User.provider_subject == subject)
    )

    if existing is not None:
        # Never silently change an account's email identity.
        if existing.email.lower() != email:
            raise IdentityConflict(
                "Google account email differs from registered email"
            )
        return existing

    email_owner = db.scalar(
        select(User).where(User.email == email)
    )

    if email_owner is not None:
        raise IdentityConflict(
            "Email already belongs to an existing account"
        )

    user = User(
        email=email,
        provider_subject=subject,
    )

    db.add(user)
    db.flush()

    return user
