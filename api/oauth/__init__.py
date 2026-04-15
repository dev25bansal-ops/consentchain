"""OAuth2/OIDC Integration for ConsentChain.

Supports:
- Google OAuth2
- Microsoft Azure AD
- Auth0
- Generic OIDC providers

DPDP Compliance:
- Users can authenticate with existing accounts
- Consent still required for data processing
- Audit trail for authentication events
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4
import secrets
import hashlib
import base64
import logging
import json

import httpx
from pydantic import BaseModel, Field, HttpUrl

logger = logging.getLogger(__name__)


class OAuthProvider(str, Enum):
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    AUTH0 = "auth0"
    CUSTOM = "custom"


@dataclass
class OAuthConfig:
    """OAuth2 provider configuration."""

    provider: OAuthProvider
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
    userinfo_url: str
    scopes: List[str]
    redirect_uri: str
    issuer_url: Optional[str] = None
    jwks_url: Optional[str] = None

    @classmethod
    def google(cls, client_id: str, client_secret: str, redirect_uri: str) -> "OAuthConfig":
        return cls(
            provider=OAuthProvider.GOOGLE,
            client_id=client_id,
            client_secret=client_secret,
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo",
            scopes=["openid", "email", "profile"],
            redirect_uri=redirect_uri,
            issuer_url="https://accounts.google.com",
            jwks_url="https://www.googleapis.com/oauth2/v3/certs",
        )

    @classmethod
    def microsoft(
        cls, client_id: str, client_secret: str, redirect_uri: str, tenant_id: str = "common"
    ) -> "OAuthConfig":
        return cls(
            provider=OAuthProvider.MICROSOFT,
            client_id=client_id,
            client_secret=client_secret,
            authorization_url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
            token_url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            userinfo_url="https://graph.microsoft.com/oidc/userinfo",
            scopes=["openid", "email", "profile"],
            redirect_uri=redirect_uri,
            issuer_url=f"https://login.microsoftonline.com/{tenant_id}/v2.0",
            jwks_url=f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
        )

    @classmethod
    def auth0(
        cls, client_id: str, client_secret: str, redirect_uri: str, domain: str
    ) -> "OAuthConfig":
        return cls(
            provider=OAuthProvider.AUTH0,
            client_id=client_id,
            client_secret=client_secret,
            authorization_url=f"https://{domain}/authorize",
            token_url=f"https://{domain}/oauth/token",
            userinfo_url=f"https://{domain}/userinfo",
            scopes=["openid", "email", "profile"],
            redirect_uri=redirect_uri,
            issuer_url=f"https://{domain}/",
            jwks_url=f"https://{domain}/.well-known/jwks.json",
        )


@dataclass
class OAuthState:
    """OAuth state for CSRF protection."""

    state: str
    code_verifier: str
    code_challenge: str
    redirect_uri: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    provider: Optional[OAuthProvider] = None

    @classmethod
    def generate(cls, redirect_uri: str, provider: Optional[OAuthProvider] = None) -> "OAuthState":
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)

        verifier_bytes = code_verifier.encode("utf-8")
        sha256_hash = hashlib.sha256(verifier_bytes).digest()
        code_challenge = base64.urlsafe_b64encode(sha256_hash).decode("utf-8").rstrip("=")

        return cls(
            state=state,
            code_verifier=code_verifier,
            code_challenge=code_challenge,
            redirect_uri=redirect_uri,
            provider=provider,
        )


@dataclass
class OAuthToken:
    """OAuth token response."""

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    scope: Optional[str] = None
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        self.expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.expires_in)

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


@dataclass
class OAuthUserInfo:
    """User information from OAuth provider."""

    provider: OAuthProvider
    provider_user_id: str
    email: Optional[str] = None
    email_verified: bool = False
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    locale: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


class OAuthService:
    """OAuth2/OIDC service for authentication."""

    def __init__(self):
        self._configs: Dict[OAuthProvider, OAuthConfig] = {}
        self._states: Dict[str, OAuthState] = {}
        self._sessions: Dict[str, OAuthToken] = {}

    def register_provider(self, config: OAuthConfig):
        """Register an OAuth provider configuration."""
        self._configs[config.provider] = config
        logger.info(f"Registered OAuth provider: {config.provider.value}")

    def get_provider(self, provider: OAuthProvider) -> Optional[OAuthConfig]:
        """Get OAuth provider configuration."""
        return self._configs.get(provider)

    def get_authorization_url(
        self,
        provider: OAuthProvider,
        redirect_uri: str,
        state: Optional[str] = None,
        extra_params: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generate OAuth authorization URL."""
        config = self._configs.get(provider)
        if not config:
            raise ValueError(f"Provider {provider.value} not configured")

        oauth_state = OAuthState.generate(redirect_uri, provider)
        self._states[oauth_state.state] = oauth_state

        params = {
            "client_id": config.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(config.scopes),
            "state": oauth_state.state,
            "code_challenge": oauth_state.code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "consent",
        }

        if extra_params:
            params.update(extra_params)

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{config.authorization_url}?{query_string}"

    async def exchange_code(
        self,
        provider: OAuthProvider,
        code: str,
        state: str,
        redirect_uri: str,
    ) -> OAuthToken:
        """Exchange authorization code for access token."""
        config = self._configs.get(provider)
        if not config:
            raise ValueError(f"Provider {provider.value} not configured")

        oauth_state = self._states.get(state)
        if not oauth_state:
            raise ValueError("Invalid or expired state")

        if datetime.now(timezone.utc) > oauth_state.created_at + timedelta(minutes=10):
            del self._states[state]
            raise ValueError("State expired")

        del self._states[state]

        data = {
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": oauth_state.code_verifier,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                config.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise ValueError(f"Token exchange failed: {response.status_code}")

            token_data = response.json()

        token = OAuthToken(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", 3600),
            refresh_token=token_data.get("refresh_token"),
            id_token=token_data.get("id_token"),
            scope=token_data.get("scope"),
        )

        session_id = str(uuid4())
        self._sessions[session_id] = token

        return token

    async def get_user_info(
        self,
        provider: OAuthProvider,
        token: OAuthToken,
    ) -> OAuthUserInfo:
        """Get user information from OAuth provider."""
        config = self._configs.get(provider)
        if not config:
            raise ValueError(f"Provider {provider.value} not configured")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                config.userinfo_url,
                headers={"Authorization": f"Bearer {token.access_token}"},
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.error(f"Userinfo request failed: {response.text}")
                raise ValueError(f"Userinfo request failed: {response.status_code}")

            user_data = response.json()

        return self._parse_user_info(provider, user_data)

    def _parse_user_info(
        self,
        provider: OAuthProvider,
        data: Dict[str, Any],
    ) -> OAuthUserInfo:
        """Parse user info based on provider."""
        if provider == OAuthProvider.GOOGLE:
            return OAuthUserInfo(
                provider=provider,
                provider_user_id=data.get("sub", ""),
                email=data.get("email"),
                email_verified=data.get("email_verified", False),
                name=data.get("name"),
                given_name=data.get("given_name"),
                family_name=data.get("family_name"),
                picture=data.get("picture"),
                locale=data.get("locale"),
                raw_data=data,
            )
        elif provider == OAuthProvider.MICROSOFT:
            return OAuthUserInfo(
                provider=provider,
                provider_user_id=data.get("sub", ""),
                email=data.get("email"),
                email_verified=data.get("email_verified", True),
                name=data.get("name"),
                given_name=data.get("given_name"),
                family_name=data.get("family_name"),
                raw_data=data,
            )
        else:
            return OAuthUserInfo(
                provider=provider,
                provider_user_id=data.get("sub", data.get("user_id", "")),
                email=data.get("email"),
                email_verified=data.get("email_verified", False),
                name=data.get("name"),
                picture=data.get("picture"),
                raw_data=data,
            )

    async def refresh_token(
        self,
        provider: OAuthProvider,
        refresh_token: str,
    ) -> OAuthToken:
        """Refresh access token using refresh token."""
        config = self._configs.get(provider)
        if not config:
            raise ValueError(f"Provider {provider.value} not configured")

        data = {
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                config.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0,
            )

            if response.status_code != 200:
                raise ValueError(f"Token refresh failed: {response.status_code}")

            token_data = response.json()

        return OAuthToken(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", 3600),
            refresh_token=token_data.get("refresh_token", refresh_token),
            id_token=token_data.get("id_token"),
        )

    async def revoke_token(
        self,
        provider: OAuthProvider,
        token: str,
    ) -> bool:
        """Revoke an access or refresh token."""
        config = self._configs.get(provider)
        if not config:
            return False

        revoke_url = None
        if provider == OAuthProvider.GOOGLE:
            revoke_url = "https://oauth2.googleapis.com/revoke"
        elif provider == OAuthProvider.MICROSOFT:
            revoke_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/logout"

        if not revoke_url:
            return True

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    revoke_url,
                    data={"token": token},
                    timeout=10.0,
                )
            return True
        except Exception as e:
            logger.error(f"Token revocation failed: {e}")
            return False


oauth_service = OAuthService()


def init_oauth_from_env():
    """Initialize OAuth providers from environment variables."""
    import os

    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if google_client_id and google_client_secret:
        redirect_uri = os.getenv(
            "GOOGLE_REDIRECT_URI", "http://localhost:8001/api/v1/oauth/callback/google"
        )
        oauth_service.register_provider(
            OAuthConfig.google(google_client_id, google_client_secret, redirect_uri)
        )

    microsoft_client_id = os.getenv("MICROSOFT_CLIENT_ID")
    microsoft_client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
    microsoft_tenant_id = os.getenv("MICROSOFT_TENANT_ID", "common")
    if microsoft_client_id and microsoft_client_secret:
        redirect_uri = os.getenv(
            "MICROSOFT_REDIRECT_URI", "http://localhost:8001/api/v1/oauth/callback/microsoft"
        )
        oauth_service.register_provider(
            OAuthConfig.microsoft(
                microsoft_client_id, microsoft_client_secret, redirect_uri, microsoft_tenant_id
            )
        )

    auth0_client_id = os.getenv("AUTH0_CLIENT_ID")
    auth0_client_secret = os.getenv("AUTH0_CLIENT_SECRET")
    auth0_domain = os.getenv("AUTH0_DOMAIN")
    if auth0_client_id and auth0_client_secret and auth0_domain:
        redirect_uri = os.getenv(
            "AUTH0_REDIRECT_URI", "http://localhost:8001/api/v1/oauth/callback/auth0"
        )
        oauth_service.register_provider(
            OAuthConfig.auth0(auth0_client_id, auth0_client_secret, redirect_uri, auth0_domain)
        )


class OAuthLoginRequest(BaseModel):
    """OAuth login request."""

    provider: OAuthProvider
    redirect_uri: str
    extra_params: Optional[Dict[str, str]] = None


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request."""

    provider: OAuthProvider
    code: str
    state: str
    redirect_uri: str


class OAuthTokenResponse(BaseModel):
    """OAuth token response."""

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None


class OAuthUserInfoResponse(BaseModel):
    """OAuth user info response."""

    provider: str
    provider_user_id: str
    email: Optional[str] = None
    email_verified: bool = False
    name: Optional[str] = None
    picture: Optional[str] = None
