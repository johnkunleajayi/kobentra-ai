"""Tests for persistent authentication sessions."""

from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth_sessions import (
    create_session,
    get_active_session,
    revoke_session,
    token_digest,
    utc_now,
)
from app.models import Base, User, AuthSession


def make_database():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def test_session_creation_and_lookup():
    engine = make_database()

    try:
        with Session(engine) as db:
            user = User(
                email="session-test@example.com",
                provider_subject="google-session-test",
            )
            db.add(user)
            db.flush()

            token = create_session(db, user.id)
            db.commit()

            assert token
            assert len(token) >= 40

            record = get_active_session(db, token)

            assert record is not None
            assert record.user_id == user.id
            assert record.token_hash == token_digest(token)
            assert record.token_hash != token

            assert get_active_session(db, "invalid-token") is None
            assert get_active_session(db, None) is None

    finally:
        engine.dispose()


def test_session_revocation():
    engine = make_database()

    try:
        with Session(engine) as db:
            user = User(
                email="revoke-test@example.com",
                provider_subject="google-revoke-test",
            )
            db.add(user)
            db.flush()

            token = create_session(db, user.id)
            db.commit()

            assert revoke_session(db, token) is True
            db.commit()

            assert get_active_session(db, token) is None
            assert revoke_session(db, token) is False

    finally:
        engine.dispose()


def test_expired_session_is_rejected():
    engine = make_database()

    try:
        with Session(engine) as db:
            user = User(
                email="expired-test@example.com",
                provider_subject="google-expired-test",
            )
            db.add(user)
            db.flush()

            token = create_session(db, user.id)
            db.commit()

            record = db.query(AuthSession).filter_by(
                token_hash=token_digest(token)
            ).one()

            record.expires_at = utc_now() - timedelta(minutes=1)
            db.commit()

            assert get_active_session(db, token) is None

    finally:
        engine.dispose()


def test_session_lifetime_validation():
    engine = make_database()

    try:
        with Session(engine) as db:
            for hours in (0, -1, 721):
                try:
                    create_session(db, "unused-user", hours)
                except ValueError:
                    pass
                else:
                    raise AssertionError(
                        "Invalid session lifetime was accepted"
                    )

    finally:
        engine.dispose()
