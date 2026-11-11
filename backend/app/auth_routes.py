"""Google OIDC authentication with database-backed OAuth state."""

import base64
import hashlib
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .admin.authorization import is_platform_owner
from .auth_sessions import (
    create_session,
    get_active_session,
    revoke_session,
)
from .google_identity import (
    IdentityConflict,
    InvalidGoogleIdentity,
    resolve_google_user,
)
from .google_token_verifier import (
    GoogleTokenVerificationError,
    verify_google_id_token,
)
from .models import User
from .oauth_browser_binding import (
    COOKIE_NAME,
    InvalidBrowserBinding,
    create_browser_binding,
    verify_browser_binding,
)
from .oauth_transactions import (
    InvalidOAuthTransaction,
    consume_transaction,
    create_transaction,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"


def config(request: Request):
    return request.app.state.settings


def engine(request: Request):
    return request.app.state.database_engine


def secure_cookie(request: Request) -> bool:
    return urlparse(config(request).google_redirect_uri).scheme == "https"


def oauth_secret(request: Request) -> str:
    value = config(request).oauth_session_secret
    if value is None or not value.get_secret_value():
        raise HTTPException(503, "Authentication unavailable")
    return value.get_secret_value()


def client_secret(request: Request) -> str:
    value = config(request).google_client_secret
    if value is None or not value.get_secret_value():
        raise HTTPException(503, "Authentication unavailable")
    return value.get_secret_value()


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def clear_binding(response: RedirectResponse) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/google/login")
async def google_login(request: Request):
    settings = config(request)

    if not settings.google_client_id:
        raise HTTPException(503, "Authentication unavailable")

    oauth_secret(request)
    client_secret(request)

    with Session(engine(request)) as db:
        state, nonce, verifier = create_transaction(db)
        db.commit()

    parameters = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": pkce_challenge(verifier),
        "code_challenge_method": "S256",
    }

    response = RedirectResponse(
        f"{AUTHORIZE_URL}?{urlencode(parameters)}",
        status_code=302,
    )

    response.set_cookie(
        COOKIE_NAME,
        create_browser_binding(state, oauth_secret(request)),
        max_age=600,
        httponly=True,
        secure=secure_cookie(request),
        samesite="lax",
        path="/",
    )

    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/google/callback")
async def google_callback(request: Request):
    settings = config(request)
    state = request.query_params.get("state")
    code = request.query_params.get("code")

    if not state:
        raise HTTPException(400, "Invalid OAuth state")

    try:
        verify_browser_binding(
            request.cookies.get(COOKIE_NAME),
            state,
            oauth_secret(request),
        )
    except InvalidBrowserBinding:
        raise HTTPException(400, "Invalid OAuth browser binding") from None

    # Commit consumption BEFORE exchanging the Google authorization code.
    # A failed exchange must not make the state reusable.
    with Session(engine(request)) as db:
        try:
            transaction = consume_transaction(db, state)
            nonce = transaction.nonce
            verifier = transaction.code_verifier
            db.commit()
        except InvalidOAuthTransaction:
            db.rollback()
            raise HTTPException(400, "OAuth transaction expired or already used") from None

    if request.query_params.get("error") or not code:
        raise HTTPException(400, "Google authentication was cancelled")

    if not settings.google_client_id:
        raise HTTPException(503, "Authentication unavailable")

    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=False,
        ) as client:
            token_response = await client.post(
                TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.google_redirect_uri,
                    "client_id": settings.google_client_id,
                    "client_secret": client_secret(request),
                    "code_verifier": verifier,
                },
            )
            token_response.raise_for_status()
            token_data = token_response.json()

            id_token = token_data.get("id_token")
            if not isinstance(id_token, str) or not id_token:
                raise GoogleTokenVerificationError()

            keys_response = await client.get(JWKS_URL)
            keys_response.raise_for_status()
            jwks = keys_response.json()

        claims = verify_google_id_token(
            id_token,
            jwks,
            settings.google_client_id,
            nonce,
        )

        # Additional multi-audience protection.
        audience = claims.get("aud")
        if isinstance(audience, list):
            if len(audience) != 1:
                raise GoogleTokenVerificationError()
        elif not isinstance(audience, str):
            raise GoogleTokenVerificationError()

        authorized_party = claims.get("azp")
        if authorized_party is not None and (authorized_party != settings.google_client_id):
            raise GoogleTokenVerificationError()

    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        GoogleTokenVerificationError,
    ):
        raise HTTPException(401, "Google identity verification failed") from None

    try:
        with Session(engine(request)) as db:
            user = resolve_google_user(db, claims)
            session_token = create_session(
                db,
                user.id,
                settings.session_lifetime_hours,
            )
            db.commit()
    except IdentityConflict:
        raise HTTPException(409, "Google identity conflicts with an existing account") from None
    except InvalidGoogleIdentity:
        raise HTTPException(401, "Invalid Google identity") from None

    response = RedirectResponse(
        settings.frontend_url,
        status_code=303,
    )
    clear_binding(response)

    response.set_cookie(
        settings.session_cookie_name,
        session_token,
        max_age=settings.session_lifetime_hours * 3600,
        httponly=True,
        secure=secure_cookie(request),
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/me")
def authenticated_user(request: Request):
    settings = config(request)
    token = request.cookies.get(settings.session_cookie_name)

    with Session(engine(request)) as db:
        active = get_active_session(db, token)
        if active is None:
            raise HTTPException(401, "Authentication required")

        user = db.get(User, active.user_id)
        if user is None:
            raise HTTPException(401, "Authentication required")

        return {
            "id": user.id,
            "email": user.email,
            "authenticated": True,
            "capabilities": {"platform_admin": is_platform_owner(user, settings)},
        }


@router.post("/logout")
def logout(request: Request):
    settings = config(request)

    # Require an approved browser origin for this state-changing request.
    origin = request.headers.get("origin")
    if origin not in settings.cors_origins:
        raise HTTPException(403, "Invalid request origin")

    token = request.cookies.get(settings.session_cookie_name)

    if token:
        with Session(engine(request)) as db:
            revoke_session(db, token)
            db.commit()

    from fastapi.responses import JSONResponse

    response = JSONResponse({"authenticated": False})
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.headers["Cache-Control"] = "no-store"
    return response
