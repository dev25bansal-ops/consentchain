"""Tests for WebAuthn (Passkey) authentication.

Covers:
- Challenge generation and storage
- Registration options creation
- Registration verification
- Authentication options creation
- Authentication verification
- Credential management (add, remove, lookup)
- Cloned authenticator detection
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import base64

from api.webauthn import (
    webauthn_service,
    WebAuthnService,
    WebAuthnUser,
    AuthenticatorTransport,
    UserVerificationRequirement,
    AttestationConveyancePreference,
    CredentialCreationOptions,
    CredentialRequestOptions,
    RegistrationResult,
    AuthenticationResult,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def fresh_webauthn():
    """Provide a fresh WebAuthnService instance."""
    return WebAuthnService(
        rp_name="Test ConsentChain",
        rp_id="localhost",
        origin="http://localhost:8001",
    )


@pytest.fixture
def test_user():
    """Provide a test WebAuthnUser."""
    return WebAuthnUser(
        user_id="test-user-123",
        username="testuser@example.com",
        display_name="Test User",
    )


# ============================================================
# Test: Challenge Generation
# ============================================================


class TestChallengeGeneration:
    """Test cryptographic challenge generation and verification."""

    def test_generate_challenge_is_unique(self, fresh_webauthn):
        """Each challenge is unique."""
        c1 = fresh_webauthn.generate_challenge()
        c2 = fresh_webauthn.generate_challenge()
        assert c1 != c2

    def test_generate_challenge_length(self, fresh_webauthn):
        """Challenges are sufficiently long (32 bytes base64url)."""
        challenge = fresh_webauthn.generate_challenge()
        # 32 bytes -> ~43 base64 chars
        assert len(challenge) >= 40

    def test_generate_challenge_is_base64url(self, fresh_webauthn):
        """Challenge is valid base64url encoding."""
        import re
        challenge = fresh_webauthn.generate_challenge()
        # base64url uses A-Z, a-z, 0-9, -, _ (no padding)
        assert re.match(r'^[A-Za-z0-9_-]+$', challenge)

    def test_store_and_verify_challenge(self, fresh_webauthn):
        """Stored challenge can be verified."""
        challenge = fresh_webauthn.generate_challenge()
        fresh_webauthn.store_challenge("user-123", challenge)

        assert fresh_webauthn.verify_challenge("user-123", challenge) is True

    def test_verify_wrong_challenge(self, fresh_webauthn):
        """Wrong challenge fails verification."""
        challenge = fresh_webauthn.generate_challenge()
        fresh_webauthn.store_challenge("user-123", challenge)

        assert fresh_webauthn.verify_challenge("user-123", "wrong-challenge") is False

    def test_verify_challenge_for_wrong_user(self, fresh_webauthn):
        """Challenge for wrong user fails."""
        challenge = fresh_webauthn.generate_challenge()
        fresh_webauthn.store_challenge("user-123", challenge)

        assert fresh_webauthn.verify_challenge("user-456", challenge) is False

    def test_verify_challenge_not_stored(self, fresh_webauthn):
        """Unstored challenge fails verification."""
        assert fresh_webauthn.verify_challenge("user-999", "any-challenge") is False

    def test_challenge_consumed_after_verify(self, fresh_webauthn):
        """Challenge is consumed (deleted) after successful verification."""
        challenge = fresh_webauthn.generate_challenge()
        fresh_webauthn.store_challenge("user-123", challenge)

        assert fresh_webauthn.verify_challenge("user-123", challenge) is True
        # Second verification should fail (challenge consumed)
        assert fresh_webauthn.verify_challenge("user-123", challenge) is False

    def test_challenge_expiry(self, fresh_webauthn):
        """Expired challenge fails verification."""
        challenge = fresh_webauthn.generate_challenge()
        # Store with 0-second TTL to simulate expiry
        fresh_webauthn.store_challenge("user-123", challenge, ttl_seconds=0)

        # Small delay to ensure expiry
        import time
        time.sleep(0.01)

        assert fresh_webauthn.verify_challenge("user-123", challenge) is False


# ============================================================
# Test: User Registration
# ============================================================


class TestUserRegistration:
    """Test user registration with WebAuthn."""

    def test_register_user(self, fresh_webauthn, test_user):
        """User can be registered."""
        fresh_webauthn.register_user(test_user)
        stored = fresh_webauthn.get_user("test-user-123")
        assert stored is not None
        assert stored.username == "testuser@example.com"

    def test_get_user_by_username(self, fresh_webauthn, test_user):
        """User lookup by username works."""
        fresh_webauthn.register_user(test_user)
        found = fresh_webauthn.get_user_by_username("testuser@example.com")
        assert found is not None
        assert found.user_id == "test-user-123"

    def test_get_nonexistent_user(self, fresh_webauthn):
        """Nonexistent user returns None."""
        assert fresh_webauthn.get_user("nonexistent") is None

    def test_get_user_by_nonexistent_username(self, fresh_webauthn):
        """Nonexistent username returns None."""
        assert fresh_webauthn.get_user_by_username("noone@example.com") is None


# ============================================================
# Test: Registration Options
# ============================================================


class TestRegistrationOptions:
    """Test creation of credential registration options."""

    def test_create_registration_options(self, fresh_webauthn, test_user):
        """Registration options contain required fields."""
        fresh_webauthn.register_user(test_user)

        options = fresh_webauthn.create_registration_options(test_user)

        assert options.rp["id"] == "localhost"
        assert options.rp["name"] == "Test ConsentChain"
        assert options.user["name"] == "testuser@example.com"
        assert options.user["displayName"] == "Test User"
        assert options.challenge is not None
        assert options.timeout == 60000
        assert options.attestation == "none"

    def test_registration_options_pub_key_algorithms(self, fresh_webauthn, test_user):
        """Registration options include supported algorithms."""
        fresh_webauthn.register_user(test_user)
        options = fresh_webauthn.create_registration_options(test_user)

        alg_ids = [p["alg"] for p in options.pubKeyCredParams]
        assert "-7" in alg_ids   # ES256
        assert "-257" in alg_ids  # RS256
        assert "-8" in alg_ids    # EdDSA

    def test_registration_options_exclude_credentials(self, fresh_webauthn, test_user):
        """Exclude credentials list is populated."""
        fresh_webauthn.register_user(test_user)

        options = fresh_webauthn.create_registration_options(
            test_user,
            exclude_credentials=["cred-1", "cred-2"],
        )

        assert len(options.excludeCredentials) == 2
        assert options.excludeCredentials[0]["id"] == "cred-1"

    def test_registration_options_authenticator_selection(self, fresh_webauthn, test_user):
        """Authenticator selection criteria are set."""
        fresh_webauthn.register_user(test_user)

        options = fresh_webauthn.create_registration_options(
            test_user,
            authenticator_type="cross-platform",
            user_verification=UserVerificationRequirement.REQUIRED,
            attestation=AttestationConveyancePreference.DIRECT,
        )

        assert options.authenticatorSelection["authenticatorAttachment"] == "cross-platform"
        assert options.authenticatorSelection["userVerification"] == "required"
        assert options.attestation == "direct"

    def test_registration_challenge_is_stored(self, fresh_webauthn, test_user):
        """Registration challenge is stored for verification."""
        fresh_webauthn.register_user(test_user)
        options = fresh_webauthn.create_registration_options(test_user)

        # The challenge should be stored and verifiable
        assert fresh_webauthn.verify_challenge("test-user-123", options.challenge) is True


# ============================================================
# Test: Registration Verification
# ============================================================


class TestRegistrationVerification:
    """Test registration response verification."""

    def test_verify_registration_missing_client_data(self, fresh_webauthn, test_user):
        """Missing client data returns error."""
        fresh_webauthn.register_user(test_user)
        fresh_webauthn.create_registration_options(test_user)

        result = fresh_webauthn.verify_registration(
            user_id="test-user-123",
            credential={},
            client_data={"challenge": "some-challenge"},
        )

        assert result.success is False
        assert "Missing client data" in result.error

    def test_verify_registration_invalid_challenge(self, fresh_webauthn, test_user):
        """Invalid challenge returns error."""
        fresh_webauthn.register_user(test_user)

        result = fresh_webauthn.verify_registration(
            user_id="test-user-123",
            credential={"response": {"clientDataJSON": "data"}},
            client_data={"challenge": "nonexistent-challenge"},
        )

        assert result.success is False
        assert "Invalid or expired challenge" in result.error

    def test_verify_registration_missing_credential_id(self, fresh_webauthn, test_user):
        """Missing credential ID returns error."""
        fresh_webauthn.register_user(test_user)
        challenge = fresh_webauthn.generate_challenge()
        fresh_webauthn.store_challenge("test-user-123", challenge)

        result = fresh_webauthn.verify_registration(
            user_id="test-user-123",
            credential={"response": {"clientDataJSON": "data"}},
            client_data={"challenge": challenge, "origin": "http://localhost:8001", "type": "webauthn.create"},
        )

        assert result.success is False
        assert "Missing credential ID" in result.error

    def test_verify_registration_wrong_type(self, fresh_webauthn, test_user):
        """Wrong client data type returns error."""
        fresh_webauthn.register_user(test_user)
        challenge = fresh_webauthn.generate_challenge()
        fresh_webauthn.store_challenge("test-user-123", challenge)

        result = fresh_webauthn.verify_registration(
            user_id="test-user-123",
            credential={"id": "new-cred-id", "response": {"clientDataJSON": "data", "attestationObject": "att"}},
            client_data={"challenge": challenge, "origin": "http://localhost:8001", "type": "webauthn.get"},
        )

        assert result.success is False
        assert "Invalid client data type" in result.error

    def test_verify_registration_success(self, fresh_webauthn, test_user):
        """Valid registration succeeds."""
        fresh_webauthn.register_user(test_user)
        challenge = fresh_webauthn.generate_challenge()
        fresh_webauthn.store_challenge("test-user-123", challenge)

        result = fresh_webauthn.verify_registration(
            user_id="test-user-123",
            credential={
                "id": "new-credential-id",
                "response": {
                    "clientDataJSON": "data",
                    "attestationObject": "attestation-data",
                },
            },
            client_data={
                "challenge": challenge,
                "origin": "http://localhost:8001",
                "type": "webauthn.create",
            },
        )

        assert result.success is True
        assert result.credential_id == "new-credential-id"
        assert result.public_key is not None

    def test_verify_registration_missing_attestation(self, fresh_webauthn, test_user):
        """Missing attestation object returns error."""
        fresh_webauthn.register_user(test_user)
        challenge = fresh_webauthn.generate_challenge()
        fresh_webauthn.store_challenge("test-user-123", challenge)

        result = fresh_webauthn.verify_registration(
            user_id="test-user-123",
            credential={"id": "cred-id", "response": {"clientDataJSON": "data"}},
            client_data={"challenge": challenge, "origin": "http://localhost:8001", "type": "webauthn.create"},
        )

        assert result.success is False
        assert "Missing attestation object" in result.error


# ============================================================
# Test: Authentication Options
# ============================================================


class TestAuthenticationOptions:
    """Test creation of authentication request options."""

    def test_create_auth_options_with_user_id(self, fresh_webauthn, test_user):
        """Auth options for known user include credential."""
        test_user.credential_id = "existing-cred-id"
        fresh_webauthn.register_user(test_user)

        options = fresh_webauthn.create_authentication_options(user_id="test-user-123")

        assert options.challenge is not None
        assert options.rpId == "localhost"
        assert options.timeout == 60000
        assert options.userVerification == "preferred"

    def test_create_auth_options_with_credential_ids(self, fresh_webauthn, test_user):
        """Auth options with specific credential IDs."""
        test_user.credential_id = "cred-1"
        test_user.transports = [AuthenticatorTransport.USB, AuthenticatorTransport.NFC]
        fresh_webauthn.register_user(test_user)
        fresh_webauthn._credentials["cred-1"] = test_user

        options = fresh_webauthn.create_authentication_options(credential_ids=["cred-1"])

        assert len(options.allowCredentials) == 1
        assert options.allowCredentials[0]["id"] == "cred-1"
        assert "usb" in options.allowCredentials[0]["transports"]

    def test_create_auth_options_unknown_credential(self, fresh_webauthn):
        """Unknown credential IDs result in empty allowCredentials."""
        options = fresh_webauthn.create_authentication_options(credential_ids=["unknown-cred"])

        assert len(options.allowCredentials) == 0

    def test_create_auth_options_no_user_no_creds(self, fresh_webauthn):
        """No user and no credentials results in empty allowCredentials."""
        options = fresh_webauthn.create_authentication_options()

        assert options.challenge is not None
        assert len(options.allowCredentials) == 0


# ============================================================
# Test: Authentication Verification
# ============================================================


class TestAuthenticationVerification:
    """Test authentication response verification."""

    def test_auth_missing_credential_id(self, fresh_webauthn):
        """Missing credential ID returns error."""
        result = fresh_webauthn.verify_authentication(
            credential={},
            client_data={"challenge": "chal", "type": "webauthn.get", "origin": "http://localhost:8001"},
        )

        assert result.success is False
        assert "Missing credential ID" in result.error

    def test_auth_unknown_credential(self, fresh_webauthn):
        """Unknown credential returns error."""
        result = fresh_webauthn.verify_authentication(
            credential={"id": "unknown-cred"},
            client_data={"challenge": "chal", "type": "webauthn.get", "origin": "http://localhost:8001"},
        )

        assert result.success is False
        assert "Unknown credential" in result.error

    def test_auth_wrong_client_data_type(self, fresh_webauthn, test_user):
        """Wrong client data type returns error."""
        test_user.credential_id = "cred-1"
        fresh_webauthn.register_user(test_user)
        fresh_webauthn._credentials["cred-1"] = test_user

        challenge = fresh_webauthn.generate_challenge()
        fresh_webauthn.store_challenge("test-user-123", challenge)

        result = fresh_webauthn.verify_authentication(
            credential={"id": "cred-1", "response": {"authenticatorData": "auth-data"}},
            client_data={"challenge": challenge, "type": "webauthn.create", "origin": "http://localhost:8001"},
        )

        assert result.success is False
        assert "Invalid client data type" in result.error

    def test_auth_expired_challenge(self, fresh_webauthn, test_user):
        """Expired challenge returns error."""
        test_user.credential_id = "cred-1"
        fresh_webauthn.register_user(test_user)
        fresh_webauthn._credentials["cred-1"] = test_user

        result = fresh_webauthn.verify_authentication(
            credential={"id": "cred-1", "response": {"authenticatorData": "auth-data"}},
            client_data={"challenge": "expired-challenge", "type": "webauthn.get", "origin": "http://localhost:8001"},
        )

        assert result.success is False
        assert "Invalid or expired challenge" in result.error

    def test_auth_missing_authenticator_data(self, fresh_webauthn, test_user):
        """Missing authenticator data returns error."""
        test_user.credential_id = "cred-1"
        fresh_webauthn.register_user(test_user)
        fresh_webauthn._credentials["cred-1"] = test_user

        challenge = fresh_webauthn.generate_challenge()
        fresh_webauthn.store_challenge("test-user-123", challenge)

        result = fresh_webauthn.verify_authentication(
            credential={"id": "cred-1", "response": {}},
            client_data={"challenge": challenge, "type": "webauthn.get", "origin": "http://localhost:8001"},
        )

        assert result.success is False
        assert "Missing authenticator data" in result.error

    def test_auth_cloned_authenticator_detection(self, fresh_webauthn, test_user):
        """Cloned authenticator detected via sign_count."""
        test_user.credential_id = "cred-1"
        test_user.sign_count = 10  # Previous sign count
        fresh_webauthn.register_user(test_user)
        fresh_webauthn._credentials["cred-1"] = test_user

        challenge = fresh_webauthn.generate_challenge()
        fresh_webauthn.store_challenge("test-user-123", challenge)

        result = fresh_webauthn.verify_authentication(
            credential={
                "id": "cred-1",
                "response": {
                    "authenticatorData": "auth-data",
                    "signatureCount": 5,  # Lower than stored = clone
                },
            },
            client_data={"challenge": challenge, "type": "webauthn.get", "origin": "http://localhost:8001"},
        )

        assert result.success is False
        assert "clone" in result.error.lower()

    def test_auth_success(self, fresh_webauthn, test_user):
        """Valid authentication succeeds and updates sign count."""
        test_user.credential_id = "cred-1"
        test_user.sign_count = 5
        fresh_webauthn.register_user(test_user)
        fresh_webauthn._credentials["cred-1"] = test_user

        challenge = fresh_webauthn.generate_challenge()
        fresh_webauthn.store_challenge("test-user-123", challenge)

        result = fresh_webauthn.verify_authentication(
            credential={
                "id": "cred-1",
                "response": {
                    "authenticatorData": "auth-data",
                    "signatureCount": 6,
                },
            },
            client_data={"challenge": challenge, "type": "webauthn.get", "origin": "http://localhost:8001"},
        )

        assert result.success is True
        assert result.user_id == "test-user-123"
        assert result.new_sign_count == 6
        assert test_user.sign_count == 6

    def test_auth_sign_count_zero_allowed(self, fresh_webauthn, test_user):
        """First authentication (sign_count=0) is allowed."""
        test_user.credential_id = "cred-1"
        test_user.sign_count = 0
        fresh_webauthn.register_user(test_user)
        fresh_webauthn._credentials["cred-1"] = test_user

        challenge = fresh_webauthn.generate_challenge()
        fresh_webauthn.store_challenge("test-user-123", challenge)

        result = fresh_webauthn.verify_authentication(
            credential={
                "id": "cred-1",
                "response": {
                    "authenticatorData": "auth-data",
                    "signatureCount": 1,
                },
            },
            client_data={"challenge": challenge, "type": "webauthn.get", "origin": "http://localhost:8001"},
        )

        assert result.success is True


# ============================================================
# Test: Credential Management
# ============================================================


class TestCredentialManagement:
    """Test credential lifecycle management."""

    def test_remove_credential(self, fresh_webauthn, test_user):
        """Removing a credential cleans up state."""
        test_user.credential_id = "cred-1"
        test_user.public_key = b"public-key-bytes"
        test_user.sign_count = 5
        fresh_webauthn.register_user(test_user)
        fresh_webauthn._credentials["cred-1"] = test_user

        result = fresh_webauthn.remove_credential("cred-1")

        assert result is True
        assert "cred-1" not in fresh_webauthn._credentials
        assert test_user.credential_id is None
        assert test_user.public_key is None
        assert test_user.sign_count == 0

    def test_remove_nonexistent_credential(self, fresh_webauthn):
        """Removing nonexistent credential returns False."""
        assert fresh_webauthn.remove_credential("nonexistent") is False


# ============================================================
# Test: WebAuthnService Configuration
# ============================================================


class TestWebAuthnConfig:
    """Test WebAuthnService configuration."""

    def test_default_config(self):
        """Default configuration uses sensible defaults."""
        service = WebAuthnService()
        assert service.rp_name == "ConsentChain"
        assert service.rp_id == "localhost"
        assert service.origin == "http://localhost:8001"

    def test_custom_config(self):
        """Custom configuration is applied."""
        service = WebAuthnService(
            rp_name="My App",
            rp_id="example.com",
            origin="https://example.com",
        )
        assert service.rp_name == "My App"
        assert service.rp_id == "example.com"
        assert service.origin == "https://example.com"
