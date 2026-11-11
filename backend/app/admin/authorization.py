import secrets

from fastapi import HTTPException, Request

from ..business.routes import Database, Identity
from ..models import User


def is_platform_owner(user, settings):
    configured = settings.platform_owner_google_subject
    return bool(
        user
        and user.provider_subject
        and configured
        and secrets.compare_digest(
            user.provider_subject.encode(), configured.get_secret_value().encode()
        )
    )


def require_platform_owner(principal: Identity, db: Database, request: Request):
    if not is_platform_owner(db.get(User, principal.user_id), request.app.state.settings):
        raise HTTPException(403, "Access denied")
    return principal
