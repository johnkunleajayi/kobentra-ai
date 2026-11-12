"""Fail closed on public deployment; local development keeps its existing defaults."""

from urllib.parse import urlparse

from sqlalchemy.engine import make_url


def validate_deployment(settings):
    if settings.vercel and settings.app_env != "production":
        raise ValueError("Vercel requires APP_ENV=production")
    if settings.app_env != "production":
        return
    if make_url(settings.database_url.get_secret_value()).get_backend_name() != "postgresql":
        raise ValueError("Public deployments require PostgreSQL")
    front = urlparse(settings.frontend_url)
    callback = urlparse(settings.google_redirect_uri)
    if (
        front.scheme != "https"
        or not front.hostname
        or front.username
        or front.password
        or front.path not in {"", "/"}
        or front.query
        or front.fragment
        or callback.scheme != "https"
        or callback.netloc != front.netloc
        or callback.path != "/api/auth/google/callback"
        or callback.query
        or callback.fragment
        or settings.cors_origins != [settings.frontend_url.rstrip("/")]
    ):
        raise ValueError(
            "Deployment requires one HTTPS frontend origin and same-origin OAuth callback"
        )
    if not all(
        (settings.google_client_id, settings.google_client_secret, settings.oauth_session_secret)
    ):
        raise ValueError("Public deployments require Google authentication configuration")
    if len(settings.oauth_session_secret.get_secret_value()) < 32:
        raise ValueError("Public deployments require a strong OAuth session secret")
    if settings.salesforce_dispatch_enabled and not all(
        (
            settings.salesforce_instance_url,
            settings.salesforce_client_id,
            settings.salesforce_client_secret,
        )
    ):
        raise ValueError("Enabled Salesforce dispatch requires server-side configuration")
