"""Tests for verified Google identity provisioning."""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.google_identity import (
    IdentityConflict,
    InvalidGoogleIdentity,
    resolve_google_user,
)
from app.models import Base, User


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


def google_claims(
    subject="google-user-123",
    email="founder@example.com",
    verified=True,
):
    return {
        "sub": subject,
        "email": email,
        "email_verified": verified,
    }


def test_new_google_user_is_created(db):
    user = resolve_google_user(db, google_claims())
    db.commit()

    assert user.id is not None
    assert user.email == "founder@example.com"
    assert user.provider_subject == "google-user-123"
    assert db.scalar(select(User).where(User.id == user.id)) is not None


def test_returning_google_user_is_reused(db):
    first = resolve_google_user(db, google_claims())
    db.commit()

    second = resolve_google_user(db, google_claims())

    assert second.id == first.id
    assert len(db.scalars(select(User)).all()) == 1


def test_existing_email_cannot_be_silently_linked(db):
    db.add(
        User(
            email="founder@example.com",
            provider_subject="different-google-account",
        )
    )
    db.commit()

    with pytest.raises(IdentityConflict):
        resolve_google_user(db, google_claims())


def test_google_subject_email_change_requires_review(db):
    resolve_google_user(db, google_claims())
    db.commit()

    with pytest.raises(IdentityConflict):
        resolve_google_user(
            db,
            google_claims(email="changed@example.com"),
        )


@pytest.mark.parametrize(
    "claims",
    [
        {"email": "founder@example.com", "email_verified": True},
        {"sub": "google-user-123", "email_verified": True},
        google_claims(verified=False),
        google_claims(subject=""),
        google_claims(email=""),
        google_claims(email="a" * 255),
    ],
)
def test_invalid_google_identity_is_rejected(db, claims):
    with pytest.raises(InvalidGoogleIdentity):
        resolve_google_user(db, claims)
