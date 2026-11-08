"""Tests for server-side OAuth transaction management."""

from datetime import timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import Base, OAuthTransaction
from app.oauth_transactions import (
    InvalidOAuthTransaction,
    consume_transaction,
    create_transaction,
    state_digest,
    utc_now,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


def test_create_transaction(db):
    state, nonce, verifier = create_transaction(db)
    db.commit()

    assert len(state) >= 32
    assert len(nonce) >= 32
    assert len(verifier) >= 43

    record = db.scalar(
        select(OAuthTransaction).where(
            OAuthTransaction.state_hash == state_digest(state)
        )
    )

    assert record is not None
    assert record.state_hash != state
    assert record.nonce == nonce
    assert record.code_verifier == verifier
    assert record.consumed_at is None


def test_transaction_can_be_consumed_once(db):
    state, _, _ = create_transaction(db)
    db.commit()

    record = consume_transaction(db, state)
    db.commit()

    assert record.consumed_at is not None

    with pytest.raises(InvalidOAuthTransaction):
        consume_transaction(db, state)


def test_invalid_state_is_rejected(db):
    with pytest.raises(InvalidOAuthTransaction):
        consume_transaction(db, "invalid-state")


def test_expired_transaction_is_rejected(db):
    state, _, _ = create_transaction(db)
    db.commit()

    record = db.scalar(
        select(OAuthTransaction).where(
            OAuthTransaction.state_hash == state_digest(state)
        )
    )

    record.expires_at = utc_now() - timedelta(minutes=1)
    db.commit()

    with pytest.raises(InvalidOAuthTransaction):
        consume_transaction(db, state)


def test_invalid_lifetime_is_rejected(db):
    for minutes in (0, -1, 11):
        with pytest.raises(ValueError):
            create_transaction(db, minutes)
