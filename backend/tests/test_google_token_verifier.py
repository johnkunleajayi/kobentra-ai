"""Security tests for Google OpenID Connect ID tokens."""

from datetime import datetime, timedelta, timezone

import pytest
from joserfc import jwt
from joserfc.jwk import RSAKey

from app.google_token_verifier import (
    GoogleTokenVerificationError,
    verify_google_id_token,
)

CLIENT_ID = "kobentra-test-client"
NONCE = "test-nonce-value"


@pytest.fixture
def signing_keys():
    private_key = RSAKey.generate_key(2048, {"kid": "test-key"})
    public_jwks = {"keys": [private_key.as_dict(private=False)]}
    return private_key, public_jwks


def make_token(private_key, **overrides):
    now = datetime.now(timezone.utc)

    claims = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "sub": "google-subject-123",
        "email": "user@example.com",
        "email_verified": True,
        "nonce": NONCE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }

    claims.update(overrides)

    return jwt.encode(
        {"alg": "RS256", "kid": "test-key"},
        claims,
        private_key,
    )


def test_valid_google_token(signing_keys):
    private_key, jwks = signing_keys
    token = make_token(private_key)

    claims = verify_google_id_token(token, jwks, CLIENT_ID, NONCE)

    assert claims["sub"] == "google-subject-123"
    assert claims["email_verified"] is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://untrusted.example"},
        {"aud": "wrong-client"},
        {"nonce": "wrong-nonce"},
        {"email_verified": False},
        {"sub": ""},
        {"email": ""},
    ],
)
def test_invalid_claims_rejected(signing_keys, overrides):
    private_key, jwks = signing_keys
    token = make_token(private_key, **overrides)

    with pytest.raises(GoogleTokenVerificationError):
        verify_google_id_token(token, jwks, CLIENT_ID, NONCE)


def test_expired_token_rejected(signing_keys):
    private_key, jwks = signing_keys
    expired = int(
        (datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp()
    )

    token = make_token(private_key, exp=expired)

    with pytest.raises(GoogleTokenVerificationError):
        verify_google_id_token(token, jwks, CLIENT_ID, NONCE)


def test_wrong_signing_key_rejected(signing_keys):
    private_key, _ = signing_keys
    other_key = RSAKey.generate_key(2048, {"kid": "test-key"})

    token = make_token(private_key)
    wrong_jwks = {"keys": [other_key.as_dict(private=False)]}

    with pytest.raises(GoogleTokenVerificationError):
        verify_google_id_token(token, wrong_jwks, CLIENT_ID, NONCE)


def test_tampered_token_rejected(signing_keys):
    private_key, jwks = signing_keys
    token = make_token(private_key)

    parts = token.split(".")
    signature = parts[2]
    parts[2] = ("A" if signature[0] != "A" else "B") + signature[1:]
    tampered = ".".join(parts)

    with pytest.raises(GoogleTokenVerificationError):
        verify_google_id_token(tampered, jwks, CLIENT_ID, NONCE)
