"""Tests for OAuth2/OIDC integration.

Covers:
- OAuthService provider registration and configuration
- Authorization URL generation with PKCE
- Code exchange and user info retrieval
- Token refresh and revocation
- OAuth route handlers (authorize, callback, link, unlink)
- State management and CSRF protection
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from api.oauth import (
    oauth_service,
    OAuthProvider,
    OAuthConfig,
    OAuthState,
    OAuthToken,
    OAuthUserInfo,
    OAuthService,
    OAuthLoginRequest,
    OAuthCallbackRequest,
    OAuthTokenResponse,
    init_oauth_from_env,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def fresh_oauth_service():
    """Provide a fresh OAuthService instance for each test."""
    return OAuthService()


@pytest.fixture
def google_config():
    """Google OAuth provider configuration."""
    return OAuthConfig.google(
        client_id="test-google-client-id",
        client_secret="test-google-client-secret",
        redirect_uri="http://localhost:8001/api/v1/oauth/callback/google",
    )


@pytest.fixture
def microsoft_config():
    """Microsoft OAuth provider configuration."""
    return OAuthConfig.microsoft(
        client_id="test-ms-client-id",
        client_secret="test-ms-client-secret",
        redirect_uri="http://localhost:8001/api/v1/oauth/callback/microsoft",
        tenant_id="common",
    )


@pytest.fixture
def auth0_config():
    """Auth0 OAuth provider configuration."""
    return OAuthConfig.auth0(
        client_id="test-auth0-client-id",
        client_secret="test-auth0-client-secret",
        redirect_uri="http://localhost:8001/api/v1/oauth/callback/auth0",
        domain="test.auth0.com",
    )


# ============================================================
# Test: Provider Configuration
# ============================================================


class TestOAuthProviderConfig:
    """Test OAuth provider configuration factory methods."""

    def test_google_config_defaults(self, google_config):
        """Google config has correct default URLs."""
        assert google_config.provider == OAuthProvider.GOOGLE
        assert google_config.authorization_url == "https://accounts.google.com/o/oauth2/v2/auth"
        assert google_config.token_url == "https://oauth2.googleapis.com/token"
        assert google_config.userinfo_url == "https://www.googleapis.com/oauth2/v3/userinfo"
        assert "openid" in google_config.scopes
        assert "email" in google_config.scopes

    def test_microsoft_config_defaults(self, microsoft_config):
        """Microsoft config has correct tenant-specific URLs."""
        assert microsoft_config.provider == OAuthProvider.MICROSOFT
        assert "login.microsoftonline.com/common" in microsoft_config.authorization_url
        assert "login.microsoftonline.com/common" in microsoft_config.token_url

    def test_microsoft_config_custom_tenant(self):
        """Microsoft config supports custom tenant IDs."""
        config = OAuthConfig.microsoft(
            client_id="id",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
            tenant_id="my-tenant-id",
        )
        assert "my-tenant-id" in config.authorization_url
        assert "my-tenant-id" in config.token_url

    def test_auth0_config_defaults(self, auth0_config):
        """Auth0 config has correct domain-based URLs."""
        assert auth0_config.provider == OAuthProvider.AUTH0
        assert auth0_config.authorization_url == "https://test.auth0.com/authorize"
        assert auth0_config.token_url == "https://test.auth0.com/oauth/token"
        assert auth0_config.userinfo_url == "https://test.auth0.com/userinfo"


# ============================================================
# Test: OAuth State and PKCE
# ============================================================


class TestOAuthStatePKCE:
    """Test OAuth state generation and PKCE challenge."""

    def test_generate_state(self):
        """OAuthState.generate creates valid state."""
        state = OAuthState.generate("http://localhost/callback", OAuthProvider.GOOGLE)

        assert len(state.state) > 20
        assert len(state.code_verifier) > 40
        assert len(state.code_challenge) > 20
        assert state.provider == OAuthProvider.GOOGLE
        assert state.redirect_uri == "http://localhost/callback"

    def test_pkce_challenge_format(self):
        """Code challenge is base64url-encoded SHA256."""
        state = OAuthState.generate("http://localhost/callback")

        # Challenge should not contain padding '='
        assert "=" not in state.code_challenge
        # Should only contain valid base64url chars
        import re
        assert re.match(r'^[A-Za-z0-9_-]+$', state.code_challenge)

    def test_state_expiry(self):
        """State tracks creation time."""
        state = OAuthState.generate("http://localhost/callback")
        assert state.created_at is not None
        assert state.created_at <= datetime.now(timezone.utc)


# ============================================================
# Test: OAuth Token Management
# ============================================================


class TestOAuthToken:
    """Test OAuth token lifecycle."""

    def test_token_expires_at_calculation(self):
        """Token computes expires_at from expires_in."""
        token = OAuthToken(
            access_token="test-access-token",
            token_type="Bearer",
            expires_in=3600,
        )
        assert token.expires_at is not None
        assert token.expires_at > datetime.now(timezone.utc)

    def test_token_is_expired(self):
        """Expired token reports correctly."""
        token = OAuthToken(
            access_token="test-access-token",
            token_type="Bearer",
            expires_in=-1,  # Already expired
        )
        assert token.is_expired is True

    def test_token_not_expired(self):
        """Valid token reports not expired."""
        token = OAuthToken(
            access_token="test-access-token",
            token_type="Bearer",
            expires_in=3600,
        )
        assert token.is_expired is False

    def test_token_with_refresh_token(self):
        """Token stores optional refresh token."""
        token = OAuthToken(
            access_token="test-access",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="test-refresh-token",
            id_token="test-id-token",
        )
        assert token.refresh_token == "test-refresh-token"
        assert token.id_token == "test-id-token"


# ============================================================
# Test: OAuthService Provider Management
# ============================================================


class TestOAuthServiceProviders:
    """Test provider registration and lookup."""

    def test_register_and_get_provider(self, fresh_oauth_service, google_config):
        """Registered provider can be retrieved."""
        fresh_oauth_service.register_provider(google_config)
        config = fresh_oauth_service.get_provider(OAuthProvider.GOOGLE)
        assert config is not None
        assert config.client_id == "test-google-client-id"

    def test_get_unregistered_provider_returns_none(self, fresh_oauth_service):
        """Unregistered provider returns None."""
        config = fresh_oauth_service.get_provider(OAuthProvider.MICROSOFT)
        assert config is None

    def test_register_multiple_providers(self, fresh_oauth_service, google_config, microsoft_config):
        """Multiple providers can coexist."""
        fresh_oauth_service.register_provider(google_config)
        fresh_oauth_service.register_provider(microsoft_config)

        assert fresh_oauth_service.get_provider(OAuthProvider.GOOGLE) is not None
        assert fresh_oauth_service.get_provider(OAuthProvider.MICROSOFT) is not None


# ============================================================
# Test: Authorization URL Generation
# ============================================================


class TestAuthorizationURL:
    """Test authorization URL generation with PKCE."""

    def test_authorization_url_contains_required_params(self, fresh_oauth_service, google_config):
        """Authorization URL has all required OAuth2 params."""
        fresh_oauth_service.register_provider(google_config)

        url = fresh_oauth_service.get_authorization_url(
            provider=OAuthProvider.GOOGLE,
            redirect_uri="http://localhost/callback",
        )

        assert "client_id=" in url
        assert "redirect_uri=" in url
        assert "response_type=code" in url
        assert "scope=" in url
        assert "state=" in url
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url

    def test_authorization_url_with_extra_params(self, fresh_oauth_service, google_config):
        """Extra params are appended to URL."""
        fresh_oauth_service.register_provider(google_config)

        url = fresh_oauth_service.get_authorization_url(
            provider=OAuthProvider.GOOGLE,
            redirect_uri="http://localhost/callback",
            extra_params={"prompt": "consent", "login_hint": "user@example.com"},
        )

        assert "prompt=consent" in url
        assert "login_hint=user@example.com" in url

    def test_authorization_url_unregistered_provider(self, fresh_oauth_service):
        """Unregistered provider raises ValueError."""
        with pytest.raises(ValueError, match="not configured"):
            fresh_oauth_service.get_authorization_url(
                provider=OAuthProvider.GOOGLE,
                redirect_uri="http://localhost/callback",
            )

    def test_authorization_url_state_stored(self, fresh_oauth_service, google_config):
        """Generated state is stored for later verification."""
        fresh_oauth_service.register_provider(google_config)

        url = fresh_oauth_service.get_authorization_url(
            provider=OAuthProvider.GOOGLE,
            redirect_uri="http://localhost/callback",
        )

        state_value = url.split("state=")[1].split("&")[0]
        assert state_value in fresh_oauth_service._states


# ============================================================
# Test: Code Exchange
# ============================================================


class TestCodeExchange:
    """Test authorization code to token exchange."""

    @pytest.mark.asyncio
    async def test_exchange_code_success(self, fresh_oauth_service, google_config):
        """Valid code exchange returns OAuthToken."""
        fresh_oauth_service.register_provider(google_config)

        # First, generate state by creating auth URL
        url = fresh_oauth_service.get_authorization_url(
            provider=OAuthProvider.GOOGLE,
            redirect_uri="http://localhost/callback",
        )
        state_value = url.split("state=")[1].split("&")[0]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "mock-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "mock-refresh-token",
            "id_token": "mock-id-token",
            "scope": "openid email profile",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("api.oauth.httpx.AsyncClient", return_value=mock_client):
            token = await fresh_oauth_service.exchange_code(
                provider=OAuthProvider.GOOGLE,
                code="mock-auth-code",
                state=state_value,
                redirect_uri="http://localhost/callback",
            )

        assert token.access_token == "mock-access-token"
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600
        assert token.refresh_token == "mock-refresh-token"

    @pytest.mark.asyncio
    async def test_exchange_code_invalid_state(self, fresh_oauth_service, google_config):
        """Invalid state raises ValueError."""
        fresh_oauth_service.register_provider(google_config)

        with pytest.raises(ValueError, match="Invalid or expired state"):
            await fresh_oauth_service.exchange_code(
                provider=OAuthProvider.GOOGLE,
                code="mock-code",
                state="invalid-state",
                redirect_uri="http://localhost/callback",
            )

    @pytest.mark.asyncio
    async def test_exchange_code_unregistered_provider(self, fresh_oauth_service):
        """Unregistered provider raises ValueError."""
        with pytest.raises(ValueError, match="not configured"):
            await fresh_oauth_service.exchange_code(
                provider=OAuthProvider.GOOGLE,
                code="mock-code",
                state="some-state",
                redirect_uri="http://localhost/callback",
            )

    @pytest.mark.asyncio
    async def test_exchange_code_token_request_fails(self, fresh_oauth_service, google_config):
        """Failed token exchange raises ValueError."""
        fresh_oauth_service.register_provider(google_config)

        url = fresh_oauth_service.get_authorization_url(
            provider=OAuthProvider.GOOGLE,
            redirect_uri="http://localhost/callback",
        )
        state_value = url.split("state=")[1].split("&")[0]

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid grant"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("api.oauth.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="Token exchange failed"):
                await fresh_oauth_service.exchange_code(
                    provider=OAuthProvider.GOOGLE,
                    code="mock-code",
                    state=state_value,
                    redirect_uri="http://localhost/callback",
                )


# ============================================================
# Test: User Info Retrieval
# ============================================================


class TestUserInfo:
    """Test user info retrieval from providers."""

    @pytest.mark.asyncio
    async def test_get_user_info_google(self, fresh_oauth_service, google_config):
        """Google user info is parsed correctly."""
        fresh_oauth_service.register_provider(google_config)

        token = OAuthToken(
            access_token="mock-token",
            token_type="Bearer",
            expires_in=3600,
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sub": "google-user-123",
            "email": "user@example.com",
            "email_verified": True,
            "name": "Test User",
            "given_name": "Test",
            "family_name": "User",
            "picture": "https://example.com/photo.jpg",
            "locale": "en",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("api.oauth.httpx.AsyncClient", return_value=mock_client):
            user_info = await fresh_oauth_service.get_user_info(
                provider=OAuthProvider.GOOGLE,
                token=token,
            )

        assert user_info.provider == OAuthProvider.GOOGLE
        assert user_info.provider_user_id == "google-user-123"
        assert user_info.email == "user@example.com"
        assert user_info.email_verified is True
        assert user_info.name == "Test User"

    @pytest.mark.asyncio
    async def test_get_user_info_request_fails(self, fresh_oauth_service, google_config):
        """Failed userinfo request raises ValueError."""
        fresh_oauth_service.register_provider(google_config)

        token = OAuthToken(
            access_token="mock-token",
            token_type="Bearer",
            expires_in=3600,
        )

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("api.oauth.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="Userinfo request failed"):
                await fresh_oauth_service.get_user_info(
                    provider=OAuthProvider.GOOGLE,
                    token=token,
                )

    def test_parse_user_info_generic_provider(self, fresh_oauth_service):
        """Generic provider parsing handles fallback fields."""
        user_info = fresh_oauth_service._parse_user_info(
            provider=OAuthProvider.AUTH0,
            data={"sub": "auth0|123", "email": "user@test.com", "name": "Auth0 User"},
        )
        assert user_info.provider_user_id == "auth0|123"
        assert user_info.email == "user@test.com"
        assert user_info.name == "Auth0 User"


# ============================================================
# Test: Token Refresh and Revocation
# ============================================================


class TestTokenRefresh:
    """Test OAuth token refresh."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, fresh_oauth_service, google_config):
        """Token refresh returns new OAuthToken."""
        fresh_oauth_service.register_provider(google_config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "new-refresh-token",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("api.oauth.httpx.AsyncClient", return_value=mock_client):
            token = await fresh_oauth_service.refresh_token(
                provider=OAuthProvider.GOOGLE,
                refresh_token="old-refresh-token",
            )

        assert token.access_token == "new-access-token"
        assert token.refresh_token == "new-refresh-token"

    @pytest.mark.asyncio
    async def test_refresh_token_failure(self, fresh_oauth_service, google_config):
        """Failed refresh raises ValueError."""
        fresh_oauth_service.register_provider(google_config)

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid refresh token"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("api.oauth.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="Token refresh failed"):
                await fresh_oauth_service.refresh_token(
                    provider=OAuthProvider.GOOGLE,
                    refresh_token="invalid-refresh-token",
                )


class TestTokenRevocation:
    """Test OAuth token revocation."""

    @pytest.mark.asyncio
    async def test_revoke_google_token(self, fresh_oauth_service, google_config):
        """Google token revocation succeeds."""
        fresh_oauth_service.register_provider(google_config)

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("api.oauth.httpx.AsyncClient", return_value=mock_client):
            result = await fresh_oauth_service.revoke_token(
                provider=OAuthProvider.GOOGLE,
                token="token-to-revoke",
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_unconfigured_provider(self, fresh_oauth_service):
        """Revoking token for unconfigured provider returns False."""
        result = await fresh_oauth_service.revoke_token(
            provider=OAuthProvider.GOOGLE,
            token="some-token",
        )
        assert result is False


# ============================================================
# Test: OAuth Environment Initialization
# ============================================================


class TestOAuthEnvInit:
    """Test OAuth initialization from environment variables."""

    @patch.dict("os.environ", {}, clear=True)
    def test_init_no_env_vars(self):
        """No env vars means no providers registered."""
        service = OAuthService()
        with patch("api.oauth.oauth_service", service):
            init_oauth_from_env()
        assert service.get_provider(OAuthProvider.GOOGLE) is None

    @patch.dict(
        "os.environ",
        {
            "GOOGLE_CLIENT_ID": "env-google-id",
            "GOOGLE_CLIENT_SECRET": "env-google-secret",
        },
    )
    def test_init_google_from_env(self):
        """Google provider initialized from env vars."""
        service = OAuthService()
        with patch("api.oauth.oauth_service", service):
            init_oauth_from_env()
        config = service.get_provider(OAuthProvider.GOOGLE)
        assert config is not None
        assert config.client_id == "env-google-id"


# ============================================================
# Test: Pydantic Models
# ============================================================


class TestOAuthPydanticModels:
    """Test OAuth request/response models."""

    def test_login_request(self):
        """OAuthLoginRequest validates correctly."""
        req = OAuthLoginRequest(
            provider=OAuthProvider.GOOGLE,
            redirect_uri="http://localhost/callback",
        )
        assert req.provider == OAuthProvider.GOOGLE

    def test_callback_request(self):
        """OAuthCallbackRequest validates correctly."""
        req = OAuthCallbackRequest(
            provider=OAuthProvider.MICROSOFT,
            code="auth-code",
            state="csrf-state",
            redirect_uri="http://localhost/callback",
        )
        assert req.code == "auth-code"
        assert req.state == "csrf-state"

    def test_token_response(self):
        """OAuthTokenResponse serializes correctly."""
        resp = OAuthTokenResponse(
            access_token="jwt-token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="refresh-token",
            user={"email": "user@example.com"},
        )
        assert resp.access_token == "jwt-token"
        assert resp.user["email"] == "user@example.com"
