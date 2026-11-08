"""Bind OAuth callbacks to the browser that initiated login."""

import hashlib
import hmac
import secrets

from itsdangerous import BadSignature, URLSafeTimedSerializer

COOKIE_NAME = "kobentra_oauth_binding"
MAX_AGE_SECONDS = 600


class InvalidBrowserBinding(Exception):
    """OAuth browser binding is invalid or expired."""


def create_browser_binding(
    state: str,
    secret_key: str,
) -> str:
    """Create a signed browser-binding cookie."""

    if not state or not secret_key:
        raise ValueError("State and secret key are required")

    serializer = URLSafeTimedSerializer(
        secret_key,
        salt="kobentra-google-oauth-binding-v1",
    )

    return serializer.dumps(
        {
            "state_hash": hashlib.sha256(
                state.encode("utf-8")
            ).hexdigest(),
            "binding": secrets.token_urlsafe(16),
        }
    )


def verify_browser_binding(
    cookie_value: str | None,
    state: str,
    secret_key: str,
) -> None:
    """Verify that the callback belongs to the initiating browser."""

    if not cookie_value or not state or not secret_key:
        raise InvalidBrowserBinding()

    serializer = URLSafeTimedSerializer(
        secret_key,
        salt="kobentra-google-oauth-binding-v1",
    )

    try:
        payload = serializer.loads(
            cookie_value,
            max_age=MAX_AGE_SECONDS,
        )

        expected = hashlib.sha256(
            state.encode("utf-8")
        ).hexdigest()

        actual = payload.get("state_hash")
        binding = payload.get("binding")

        if not isinstance(actual, str):
            raise InvalidBrowserBinding()

        if not isinstance(binding, str) or len(binding) < 16:
            raise InvalidBrowserBinding()

        if not hmac.compare_digest(actual, expected):
            raise InvalidBrowserBinding()

    except (BadSignature, TypeError, ValueError):
        raise InvalidBrowserBinding() from None
