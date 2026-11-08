"""Google OpenID Connect ID-token verification."""

from typing import Any

from joserfc import jwt
from joserfc.jwk import KeySet
from joserfc.jwt import JWTClaimsRegistry


class GoogleTokenVerificationError(Exception):
    """Google ID token could not be verified."""


def verify_google_id_token(
    id_token: str,
    jwks: dict[str, Any],
    client_id: str,
    expected_nonce: str,
) -> dict[str, Any]:
    """Verify a Google ID token against trusted Google JWKS.

    JWKS must be retrieved from Google's trusted OIDC configuration.
    Never accept keys supplied by the token itself.
    """

    if not all(
        isinstance(value, str) and value
        for value in (id_token, client_id, expected_nonce)
    ):
        raise GoogleTokenVerificationError()

    try:
        keys = KeySet.import_key_set(jwks)

        token = jwt.decode(
            id_token,
            keys,
            algorithms=["RS256"],
        )

        claims = token.claims

        registry = JWTClaimsRegistry(
            iss={
                "essential": True,
                "values": [
                    "https://accounts.google.com",
                    "accounts.google.com",
                ],
            },
            aud={
                "essential": True,
                "value": client_id,
            },
            exp={"essential": True},
            iat={"essential": True},
            sub={"essential": True},
            nonce={
                "essential": True,
                "value": expected_nonce,
            },
        )

        registry.validate(claims)

        if not isinstance(claims.get("sub"), str) or not claims["sub"]:
            raise GoogleTokenVerificationError()

        if not isinstance(claims.get("email"), str) or not claims["email"]:
            raise GoogleTokenVerificationError()

        if claims.get("email_verified") is not True:
            raise GoogleTokenVerificationError()

        return dict(claims)

    except GoogleTokenVerificationError:
        raise

    except Exception:
        raise GoogleTokenVerificationError() from None
