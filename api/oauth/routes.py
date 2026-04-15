"""OAuth2/OIDC API Routes for ConsentChain.

Production-ready route handlers for OAuth2 authentication flows.
Integrates with the existing OAuthService and JWT infrastructure.
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import os
import logging
import hashlib

from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.oauth import (
    oauth_service,
    OAuthProvider,
    OAuthToken,
    OAuthUserInfo,
    OAuthLoginRequest,
    OAuthCallbackRequest,
    OAuthTokenResponse,
    OAuthUserInfoResponse,
    init_oauth_from_env,
)
from api.dependencies import get_session
from api.database import DataPrincipalDB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/oauth", tags=["OAuth2/OIDC"])

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JWT_SECRET = os.getenv("JWT_SECRET", "insecure-dev-secret-change-in-production")
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
COOKIE_SECURE = os.getenv("ENVIRONMENT", "development") == "production"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


class OAuthAuthorizeResponse(BaseModel):
    """Response containing the authorization URL to redirect the user to."""

    authorization_url: str = Field(..., description="URL to redirect the user for OAuth consent")
    state: str = Field(..., description="CSRF state parameter")
    provider: str = Field(..., description="OAuth provider name")


class OAuthCallbackResponse(BaseModel):
    """Response after successful OAuth callback."""

    success: bool = Field(..., description="Whether authentication succeeded")
    access_token: str = Field(..., description="JWT access token for the session")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    user: dict = Field(..., description="Authenticated user information")
    is_new_user: bool = Field(default=False, description="Whether this is a first-time login")
    linked_accounts: List[str] = Field(default_factory=list, description="Linked OAuth providers")


class OAuthProviderInfo(BaseModel):
    """Information about an available OAuth provider."""

    name: str = Field(..., description="Provider identifier")
    display_name: str = Field(..., description="Human-readable provider name")
    configured: bool = Field(..., description="Whether the provider is configured")
    scopes: List[str] = Field(default_factory=list, description="OAuth scopes requested")
    authorization_url: Optional[str] = Field(None, description="Provider authorization URL")


class OAuthProvidersResponse(BaseModel):
    """Response listing all available OAuth providers."""

    providers: List[OAuthProviderInfo]
    default_redirect_uri: Optional[str] = Field(None, description="Default callback URI")


class OAuthLinkRequest(BaseModel):
    """Request to link an OAuth account to an existing user."""

    provider: OAuthProvider = Field(..., description="OAuth provider")
    code: str = Field(..., description="Authorization code from OAuth callback")
    state: str = Field(..., description="OAuth state parameter")
    redirect_uri: str = Field(..., description="Redirect URI used in the authorization request")
    principal_id: str = Field(..., description="Existing user principal ID to link to")
    signature: str = Field(..., description="Wallet signature for ownership verification")
    message: str = Field(..., description="Message that was signed")


class OAuthLinkResponse(BaseModel):
    """Response after successfully linking an OAuth account."""

    success: bool = Field(..., description="Whether linking succeeded")
    provider: str = Field(..., description="Linked provider name")
    provider_user_id: str = Field(..., description="Provider's user identifier")
    principal_id: str = Field(..., description="Principal ID the account was linked to")
    message: str = Field(..., description="Success message")


class OAuthUnlinkResponse(BaseModel):
    """Response after unlinking an OAuth account."""

    success: bool = Field(..., description="Whether unlinking succeeded")
    provider: str = Field(..., description="Unlinked provider name")
    principal_id: str = Field(..., description="Principal ID the account was unlinked from")
    message: str = Field(..., description="Success message")


class OAuthAuthorizeQuery(BaseModel):
    """Query parameters for the authorize endpoint."""

    redirect_uri: str = Field(..., description="URI to redirect after OAuth completion")
    prompt: Optional[str] = Field(None, description="OIDC prompt parameter (e.g. 'consent', 'login')")
    login_hint: Optional[str] = Field(None, description="Hint to the provider about the user identity")


class OAuthCallbackQuery(BaseModel):
    """Query parameters for the callback endpoint."""

    code: str = Field(..., description="Authorization code from provider")
    state: str = Field(..., description="State parameter for CSRF verification")
    redirect_uri: str = Field(..., description="Redirect URI used in authorization request")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_jwt_tokens(principal_id: str, wallet_address: Optional[str] = None) -> dict:
    """Create access and refresh JWT tokens for a principal."""
    import jwt

    now = datetime.now(timezone.utc)

    access_payload = {
        "sub": principal_id,
        "wallet_address": wallet_address,
        "type": "access",
        "auth_method": "oauth",
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRY_HOURS),
        "jti": str(uuid4()),
    }

    refresh_payload = {
        "sub": principal_id,
        "wallet_address": wallet_address,
        "type": "refresh",
        "auth_method": "oauth",
        "iat": now,
        "exp": now + timedelta(days=7),
        "jti": str(uuid4()),
    }

    access_token = jwt.encode(access_payload, JWT_SECRET, algorithm="HS256")
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm="HS256")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": JWT_EXPIRY_HOURS * 3600,
    }


def _set_session_cookies(
    response: Response,
    session_id: str,
    access_token: str,
    refresh_token: str,
) -> None:
    """Set secure HTTP-only cookies for session management."""
    response.set_cookie(
        key="oauth_session_id",
        value=session_id,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=JWT_EXPIRY_HOURS * 3600,
        path="/api/v1/oauth",
    )
    response.set_cookie(
        key="oauth_access_token",
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=JWT_EXPIRY_HOURS * 3600,
        path="/api/v1",
    )
    response.set_cookie(
        key="oauth_refresh_token",
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=7 * 24 * 3600,
        path="/api/v1/oauth",
    )


def _get_or_create_principal(
    session: AsyncSession,
    user_info: OAuthUserInfo,
) -> tuple:
    """
    Find or create a DataPrincipal for the OAuth user.

    Returns (principal, is_new_user).
    """
    from core.crypto import CryptoUtils

    # Try to find existing principal by email hash
    email_hash = hashlib.sha256(user_info.email.encode()).hexdigest() if user_info.email else None

    if email_hash:
        result = session.execute(
            select(DataPrincipalDB).where(DataPrincipalDB.email_hash == email_hash)
        )
        principal = result.scalar_one_or_none()
        if principal:
            return principal, False

    # Create a new principal
    principal = DataPrincipalDB(
        wallet_address=f"oauth_{user_info.provider.value}_{user_info.provider_user_id}",
        email_hash=email_hash or hashlib.sha256(f"unknown_{uuid4()}".encode()).hexdigest(),
        preferred_language=user_info.locale or "en",
    )
    session.add(principal)
    return principal, True


def _verify_wallet_signature(wallet_address: str, message: str, signature: str) -> bool:
    """Verify the wallet signature for account linking."""
    from core.crypto import AlgorandSignatureVerifier

    try:
        return AlgorandSignatureVerifier.verify_algorand_signature(message, signature, wallet_address)
    except Exception as e:
        logger.warning(f"Signature verification failed: {e}")
        return False


async def _get_user_from_jwt(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Extract and validate JWT from Authorization header.

    Used as a dependency for protected OAuth endpoints.
    """
    import jwt

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )

    token = auth_header[7:]  # Strip "Bearer "

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

        if payload.get("type") not in ("access", "refresh"):
            raise HTTPException(status_code=401, detail="Invalid token type")

        # Check token is not blacklisted
        from api.database import TokenBlacklistDB
        from datetime import datetime, timezone

        jti = payload.get("jti")
        if jti:
            blacklist_result = await session.execute(
                select(TokenBlacklistDB).where(
                    TokenBlacklistDB.jti == jti,
                    TokenBlacklistDB.expires_at > datetime.now(timezone.utc),
                )
            )
            if blacklist_result.scalar_one_or_none():
                raise HTTPException(status_code=401, detail="Token has been revoked")

        return payload

    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@router.on_event("startup")
async def setup_oauth():
    """Initialize OAuth providers on startup."""
    init_oauth_from_env()
    logger.info("OAuth providers initialized")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/authorize/{provider}",
    response_model=OAuthAuthorizeResponse,
    summary="Initiate OAuth authorization flow",
    description=(
        "Start the OAuth2 authorization flow for the specified provider. "
        "Returns an authorization URL to redirect the user to. "
        "Supports PKCE (Proof Key for Code Exchange) for enhanced security."
    ),
    responses={
        200: {"description": "Authorization URL generated successfully"},
        400: {"description": "Provider not configured or invalid provider"},
        422: {"description": "Validation error"},
    },
)
async def oauth_authorize(
    provider: OAuthProvider,
    redirect_uri: str = Query(
        ..., description="URI to redirect after OAuth completion", examples=["http://localhost:3000/auth/callback"]
    ),
    prompt: Optional[str] = Query(None, description="OIDC prompt parameter", examples=["consent"]),
    login_hint: Optional[str] = Query(None, description="Login hint for the provider"),
):
    """
    Initiate OAuth2 authorization flow.

    Generates a PKCE-protected authorization URL and redirects the user
    to the OAuth provider's consent screen.
    """
    config = oauth_service.get_provider(provider)
    if not config:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{provider.value}' is not configured. Set the required environment variables.",
        )

    extra_params = {}
    if prompt:
        extra_params["prompt"] = prompt
    if login_hint:
        extra_params["login_hint"] = login_hint

    try:
        authorization_url = oauth_service.get_authorization_url(
            provider=provider,
            redirect_uri=redirect_uri,
            extra_params=extra_params if extra_params else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Extract state from the URL for the response
    state = authorization_url.split("state=")[1].split("&")[0]

    logger.info(f"OAuth authorize initiated for provider: {provider.value}")

    return OAuthAuthorizeResponse(
        authorization_url=authorization_url,
        state=state,
        provider=provider.value,
    )


@router.get(
    "/authorize/{provider}/redirect",
    summary="Redirect to OAuth provider (browser-friendly)",
    description=(
        "Directly redirects the browser to the OAuth provider's authorization page. "
        "Use this for direct browser flows instead of getting a URL back."
    ),
    responses={
        307: {"description": "Redirect to OAuth provider"},
        400: {"description": "Provider not configured"},
    },
)
async def oauth_authorize_redirect(
    provider: OAuthProvider,
    redirect_uri: str = Query(..., description="Callback URI after OAuth completion"),
):
    """Redirect browser directly to OAuth provider."""
    config = oauth_service.get_provider(provider)
    if not config:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{provider.value}' is not configured.",
        )

    try:
        authorization_url = oauth_service.get_authorization_url(
            provider=provider,
            redirect_uri=redirect_uri,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return RedirectResponse(url=authorization_url, status_code=307)


@router.get(
    "/callback/{provider}",
    response_model=OAuthCallbackResponse,
    summary="Handle OAuth callback",
    description=(
        "Handles the OAuth2 callback from the provider. Exchanges the authorization "
        "code for tokens, retrieves user info, creates or finds the principal, "
        "and returns JWT tokens."
    ),
    responses={
        200: {"description": "Authentication successful, tokens returned"},
        400: {"description": "Invalid state, expired code, or token exchange failed"},
        500: {"description": "Internal server error during authentication"},
    },
)
async def oauth_callback(
    provider: OAuthProvider,
    code: str = Query(..., description="Authorization code from OAuth provider"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    redirect_uri: str = Query(..., description="Redirect URI used in authorization request"),
    session: AsyncSession = Depends(get_session),
):
    """
    Handle OAuth2 callback and exchange code for tokens.

    This endpoint:
    1. Validates the OAuth state parameter (CSRF protection)
    2. Exchanges the authorization code for access tokens
    3. Fetches user information from the provider
    4. Finds or creates a DataPrincipal in the database
    5. Returns JWT access and refresh tokens
    """
    try:
        # Exchange authorization code for access token
        token = await oauth_service.exchange_code(
            provider=provider,
            code=code,
            state=state,
            redirect_uri=redirect_uri,
        )

        # Get user information from provider
        user_info = await oauth_service.get_user_info(provider, token)

        logger.info(f"OAuth callback successful for provider: {provider.value}, email: {user_info.email}")

    except ValueError as e:
        logger.warning(f"OAuth callback validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Authentication failed. Please try again.")

    try:
        # Find or create principal
        principal, is_new_user = _get_or_create_principal(session, user_info)
        await session.commit()

        # Generate JWT tokens
        tokens = _create_jwt_tokens(
            principal_id=str(principal.id),
            wallet_address=principal.wallet_address,
        )

        linked_accounts = [provider.value]  # At minimum, this provider is linked

        user_data = {
            "principal_id": str(principal.id),
            "provider": user_info.provider.value,
            "provider_user_id": user_info.provider_user_id,
            "email": user_info.email,
            "name": user_info.name,
            "picture": user_info.picture,
            "email_verified": user_info.email_verified,
        }

        response_data = OAuthCallbackResponse(
            success=True,
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="Bearer",
            expires_in=tokens["expires_in"],
            user=user_data,
            is_new_user=is_new_user,
            linked_accounts=linked_accounts,
        )

        logger.info(
            f"Principal {'created' if is_new_user else 'found'}: {principal.id} "
            f"via OAuth provider {provider.value}"
        )

        return response_data

    except Exception as e:
        await session.rollback()
        logger.error(f"Database error during OAuth callback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to complete authentication. Please try again.",
        )


@router.get(
    "/providers",
    response_model=OAuthProvidersResponse,
    summary="List available OAuth providers",
    description="Returns all configured OAuth providers with their status and scopes.",
)
async def list_oauth_providers():
    """List all available OAuth providers and their configuration status."""
    providers = []
    for provider_enum in OAuthProvider:
        if provider_enum == OAuthProvider.CUSTOM:
            continue  # Skip generic CUSTOM provider

        config = oauth_service.get_provider(provider_enum)
        providers.append(
            OAuthProviderInfo(
                name=provider_enum.value,
                display_name=provider_enum.value.title(),
                configured=config is not None,
                scopes=config.scopes if config else [],
                authorization_url=config.authorization_url if config else None,
            )
        )

    # Build a sensible default redirect URI
    default_redirect = None
    first_configured = next((p for p in providers if p.configured), None)
    if first_configured:
        config = oauth_service.get_provider(OAuthProvider(first_configured.name))
        if config:
            default_redirect = config.redirect_uri

    return OAuthProvidersResponse(
        providers=providers,
        default_redirect_uri=default_redirect,
    )


@router.post(
    "/link",
    response_model=OAuthLinkResponse,
    summary="Link OAuth account to existing user",
    description=(
        "Link an OAuth identity to an existing DataPrincipal account. "
        "Requires wallet signature to prove ownership of the principal."
    ),
    responses={
        200: {"description": "OAuth account linked successfully"},
        400: {"description": "Invalid signature, provider, or OAuth code"},
        404: {"description": "Principal not found"},
        409: {"description": "OAuth account already linked to another principal"},
    },
)
async def oauth_link_account(
    request: OAuthLinkRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Link an OAuth account to an existing DataPrincipal.

    Flow:
    1. Verify wallet signature to prove principal ownership
    2. Exchange OAuth code for user info
    3. Check if the OAuth identity is already linked
    4. Create the link in the database
    """
    from uuid import UUID
    from sqlalchemy import select, insert
    from api.database import OAuthAccountDB

    # 1. Verify principal exists
    try:
        principal_uuid = UUID(request.principal_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid principal ID format")

    result = await session.execute(
        select(DataPrincipalDB).where(DataPrincipalDB.id == principal_uuid)
    )
    principal = result.scalar_one_or_none()
    if not principal:
        raise HTTPException(status_code=404, detail="Principal not found")

    # 2. Verify wallet signature
    if not _verify_wallet_signature(principal.wallet_address, request.message, request.signature):
        raise HTTPException(
            status_code=400,
            detail="Invalid signature. You must sign the message with your wallet to prove ownership.",
        )

    # 3. Exchange OAuth code for user info
    try:
        token = await oauth_service.exchange_code(
            provider=request.provider,
            code=request.code,
            state=request.state,
            redirect_uri=request.redirect_uri,
        )
        user_info = await oauth_service.get_user_info(request.provider, token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {e}")
    except Exception as e:
        logger.error(f"OAuth link error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to link OAuth account")

    # 4. Check if OAuth account is already linked elsewhere
    existing = await session.execute(
        select(OAuthAccountDB).where(
            OAuthAccountDB.provider == request.provider.value,
            OAuthAccountDB.provider_user_id == user_info.provider_user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"This {request.provider.value} account is already linked to another user.",
        )

    # 5. Check if this principal already linked this provider
    existing_link = await session.execute(
        select(OAuthAccountDB).where(
            OAuthAccountDB.principal_id == principal_uuid,
            OAuthAccountDB.provider == request.provider.value,
        )
    )
    if existing_link.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"This principal already has a linked {request.provider.value} account.",
        )

    # 6. Create the link
    oauth_account = OAuthAccountDB(
        principal_id=principal_uuid,
        provider=request.provider.value,
        provider_user_id=user_info.provider_user_id,
        email=user_info.email,
        name=user_info.name,
        picture=user_info.picture,
        access_token_encrypted=token.access_token,  # In production, encrypt this
        refresh_token_encrypted=token.refresh_token,  # In production, encrypt this
        token_expires_at=token.expires_at,
    )
    session.add(oauth_account)
    await session.commit()

    logger.info(
        f"OAuth account linked: {request.provider.value} -> principal {principal.id}"
    )

    return OAuthLinkResponse(
        success=True,
        provider=request.provider.value,
        provider_user_id=user_info.provider_user_id,
        principal_id=str(principal.id),
        message=f"Successfully linked {request.provider.value} account.",
    )


@router.post(
    "/unlink/{provider}",
    response_model=OAuthUnlinkResponse,
    summary="Unlink OAuth account",
    description=(
        "Remove a linked OAuth account from a DataPrincipal. "
        "Requires the principal's JWT token for authentication."
    ),
    responses={
        200: {"description": "OAuth account unlinked successfully"},
        400: {"description": "Cannot unlink the last authentication method"},
        404: {"description": "OAuth link not found"},
    },
)
async def oauth_unlink_account(
    provider: OAuthProvider,
    principal_id: str = Query(..., description="Principal ID to unlink from"),
    session: AsyncSession = Depends(get_session),
    user: dict = Depends(_get_user_from_jwt),
):
    """
    Unlink an OAuth account from a DataPrincipal.

    Security:
    - Requires valid JWT token for the principal
    - Verifies the principal matches the requesting user
    - Prevents unlinking the last auth method
    """
    from uuid import UUID
    from sqlalchemy import select, delete
    from api.database import OAuthAccountDB

    # Verify ownership
    if str(user.get("sub")) != principal_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        principal_uuid = UUID(principal_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid principal ID format")

    # Find the OAuth link
    result = await session.execute(
        select(OAuthAccountDB).where(
            OAuthAccountDB.principal_id == principal_uuid,
            OAuthAccountDB.provider == provider.value,
        )
    )
    oauth_account = result.scalar_one_or_none()
    if not oauth_account:
        raise HTTPException(
            status_code=404,
            detail=f"No linked {provider.value} account found for this principal.",
        )

    # Check how many auth methods this principal has
    all_oauth_links = await session.execute(
        select(OAuthAccountDB).where(OAuthAccountDB.principal_id == principal_uuid)
    )
    oauth_links = all_oauth_links.scalars().all()

    # If this is the only OAuth link and the principal has no wallet-based auth, block it
    # (A principal linked only via OAuth should keep at least one OAuth provider)
    if len(oauth_links) <= 1:
        # Check if principal has a real wallet address (not oauth-generated)
        principal_result = await session.execute(
            select(DataPrincipalDB).where(DataPrincipalDB.id == principal_uuid)
        )
        principal = principal_result.scalar_one_or_none()
        if principal and principal.wallet_address.startswith("oauth_"):
            raise HTTPException(
                status_code=400,
                detail="Cannot unlink the last authentication method. Link another provider first.",
            )

    # Perform the unlink
    provider_name = oauth_account.provider
    await session.execute(
        delete(OAuthAccountDB).where(OAuthAccountDB.id == oauth_account.id)
    )
    await session.commit()

    logger.info(f"OAuth account unlinked: {provider.value} from principal {principal_id}")

    return OAuthUnlinkResponse(
        success=True,
        provider=provider_name,
        principal_id=principal_id,
        message=f"Successfully unlinked {provider_name} account.",
    )


@router.get(
    "/linked-accounts",
    summary="Get linked OAuth accounts for current user",
    description="Returns all OAuth providers linked to the authenticated user.",
    responses={
        200: {"description": "List of linked OAuth accounts"},
        401: {"description": "Unauthorized - invalid or missing JWT"},
    },
)
async def get_linked_accounts(
    principal_id: str = Query(..., description="Principal ID to query"),
    session: AsyncSession = Depends(get_session),
    user: dict = Depends(_get_user_from_jwt),
):
    """Get all OAuth accounts linked to the current user."""
    from uuid import UUID
    from sqlalchemy import select
    from api.database import OAuthAccountDB

    # Verify ownership
    if str(user.get("sub")) != principal_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        principal_uuid = UUID(principal_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid principal ID format")

    result = await session.execute(
        select(OAuthAccountDB).where(OAuthAccountDB.principal_id == principal_uuid)
    )
    oauth_accounts = result.scalars().all()

    linked = []
    for acct in oauth_accounts:
        linked.append({
            "provider": acct.provider,
            "provider_user_id": acct.provider_user_id,
            "email": acct.email,
            "name": acct.name,
            "linked_at": acct.created_at.isoformat() if acct.created_at else None,
        })

    return {
        "principal_id": principal_id,
        "linked_accounts": linked,
        "count": len(linked),
    }


# ---------------------------------------------------------------------------
# Browser-friendly Cookie-Based Callback
# ---------------------------------------------------------------------------


@router.get(
    "/callback/{provider}/browser",
    summary="OAuth callback with browser cookies (redirect-based)",
    description=(
        "OAuth callback that sets HTTP-only cookies and redirects to the frontend. "
        "Use this for traditional browser-based OAuth flows."
    ),
    responses={
        302: {"description": "Redirect to frontend with tokens in cookies"},
        400: {"description": "OAuth callback failed"},
    },
)
async def oauth_callback_browser(
    provider: OAuthProvider,
    code: str = Query(...),
    state: str = Query(...),
    redirect_uri: str = Query(...),
    frontend_redirect: str = Query(
        default="http://localhost:3000/auth/callback",
        description="Frontend URL to redirect after setting cookies",
    ),
    session: AsyncSession = Depends(get_session),
):
    """
    Browser-friendly OAuth callback.

    Sets HTTP-only cookies with JWT tokens and redirects to the frontend.
    This is the recommended flow for browser-based applications.
    """
    try:
        token = await oauth_service.exchange_code(
            provider=provider,
            code=code,
            state=state,
            redirect_uri=redirect_uri,
        )
        user_info = await oauth_service.get_user_info(provider, token)

        principal, is_new_user = _get_or_create_principal(session, user_info)
        await session.commit()

        tokens = _create_jwt_tokens(
            principal_id=str(principal.id),
            wallet_address=principal.wallet_address,
        )

        session_id = str(uuid4())

        response = RedirectResponse(
            url=f"{frontend_redirect}?success=true&provider={provider.value}",
            status_code=302,
        )

        _set_session_cookies(
            response,
            session_id=session_id,
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
        )

        # Set additional user info cookie (non-sensitive, readable by JS)
        response.set_cookie(
            key="oauth_user",
            value=f"{{\"provider\":\"{provider.value}\",\"email\":\"{user_info.email or ''}\",\"is_new\":{str(is_new_user).lower()}}}",
            httponly=False,  # Accessible to frontend JS
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            max_age=300,  # 5 minutes - frontend should read and discard
            path="/",
        )

        logger.info(
            f"OAuth browser callback complete for {provider.value}, "
            f"principal {'created' if is_new_user else 'found'}: {principal.id}"
        )

        return response

    except ValueError as e:
        logger.warning(f"OAuth browser callback error: {e}")
        return RedirectResponse(
            url=f"{frontend_redirect}?error={e}",
            status_code=302,
        )
    except Exception as e:
        logger.error(f"OAuth browser callback error: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{frontend_redirect}?error=authentication_failed",
            status_code=302,
        )
