"""Google OpenID Connect client configuration."""

from authlib.integrations.starlette_client import OAuth

from .config import Settings


def create_google_oauth(settings: Settings) -> OAuth:
    """Configure Google's OpenID Connect client."""

    if not settings.google_client_id:
        raise ValueError("Google Client ID is not configured")

    if not settings.google_client_secret:
        raise ValueError("Google Client Secret is not configured")

    client_secret = settings.google_client_secret.get_secret_value()

    if not client_secret:
        raise ValueError("Google Client Secret is empty")

    oauth = OAuth()

    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=client_secret,
        server_metadata_url=(
            "https://accounts.google.com/.well-known/openid-configuration"
        ),
        client_kwargs={
            "scope": "openid email profile",
            "code_challenge_method": "S256",
        },
    )

    return oauth
