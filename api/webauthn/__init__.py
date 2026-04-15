from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import secrets
import base64
import hashlib
import logging
import os

logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, rsa, padding
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    from cryptography.exceptions import InvalidSignature

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography not available - WebAuthn features limited")


class AuthenticatorTransport(str, Enum):
    USB = "usb"
    NFC = "nfc"
    BLE = "ble"
    INTERNAL = "internal"
    HYBRID = "hybrid"
    SMART_CARD = "smart-card"


class PublicKeyCredentialType(str, Enum):
    PUBLIC_KEY = "public-key"


class UserVerificationRequirement(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    DISCOURAGED = "discouraged"


class AttestationConveyancePreference(str, Enum):
    NONE = "none"
    INDIRECT = "indirect"
    DIRECT = "direct"
    ENTERPRISE = "enterprise"


@dataclass
class WebAuthnUser:
    user_id: str
    username: str
    display_name: str
    credential_id: Optional[str] = None
    public_key: Optional[bytes] = None
    sign_count: int = 0
    transports: List[AuthenticatorTransport] = field(default_factory=list)
    aaguid: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CredentialCreationOptions:
    rp: Dict[str, str]
    user: Dict[str, str]
    challenge: str
    pubKeyCredParams: List[Dict[str, str]]
    timeout: int
    attestation: str
    authenticatorSelection: Dict[str, Any]
    excludeCredentials: List[Dict[str, Any]]


@dataclass
class CredentialRequestOptions:
    challenge: str
    timeout: int
    rpId: str
    allowCredentials: List[Dict[str, Any]]
    userVerification: str


@dataclass
class RegistrationResult:
    success: bool
    credential_id: Optional[str] = None
    public_key: Optional[bytes] = None
    sign_count: int = 0
    aaguid: Optional[str] = None
    error: Optional[str] = None


@dataclass
class AuthenticationResult:
    success: bool
    user_id: Optional[str] = None
    new_sign_count: int = 0
    error: Optional[str] = None


class WebAuthnService:
    def __init__(
        self,
        rp_name: str = "ConsentChain",
        rp_id: Optional[str] = None,
        origin: Optional[str] = None,
    ):
        self.rp_name = rp_name
        self.rp_id = rp_id or os.getenv("WEBAUTHN_RP_ID", "localhost")
        self.origin = origin or os.getenv("WEBAUTHN_ORIGIN", "http://localhost:8001")
        self._challenges: Dict[str, Tuple[str, datetime]] = {}
        self._users: Dict[str, WebAuthnUser] = {}
        self._credentials: Dict[str, WebAuthnUser] = {}

    def generate_challenge(self) -> str:
        challenge_bytes = secrets.token_bytes(32)
        return base64.urlsafe_b64encode(challenge_bytes).decode().rstrip("=")

    def store_challenge(self, user_id: str, challenge: str, ttl_seconds: int = 300):
        self._challenges[user_id] = (challenge, datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds))

    def verify_challenge(self, user_id: str, challenge: str) -> bool:
        if user_id not in self._challenges:
            return False

        stored_challenge, expiry = self._challenges[user_id]
        if datetime.now(timezone.utc) > expiry:
            del self._challenges[user_id]
            return False

        if stored_challenge != challenge:
            return False

        del self._challenges[user_id]
        return True

    def create_registration_options(
        self,
        user: WebAuthnUser,
        exclude_credentials: Optional[List[str]] = None,
        authenticator_type: str = "platform",
        user_verification: UserVerificationRequirement = UserVerificationRequirement.PREFERRED,
        attestation: AttestationConveyancePreference = AttestationConveyancePreference.NONE,
    ) -> CredentialCreationOptions:
        challenge = self.generate_challenge()
        self.store_challenge(user.user_id, challenge)

        exclude_list: List[Dict[str, Any]] = []
        if exclude_credentials:
            for cred_id in exclude_credentials:
                exclude_list.append(
                    {
                        "type": "public-key",
                        "id": cred_id,
                        "transports": ["internal", "hybrid"],
                    }
                )

        pub_key_cred_params = [
            {"type": "public-key", "alg": "-7"},  # ES256
            {"type": "public-key", "alg": "-257"},  # RS256
            {"type": "public-key", "alg": "-8"},  # EdDSA
        ]

        authenticator_selection = {
            "authenticatorAttachment": authenticator_type,
            "residentKey": "preferred",
            "requireResidentKey": False,
            "userVerification": user_verification.value,
        }

        return CredentialCreationOptions(
            rp={"id": self.rp_id, "name": self.rp_name},
            user={
                "id": base64.urlsafe_b64encode(user.user_id.encode()).decode().rstrip("="),
                "name": user.username,
                "displayName": user.display_name,
            },
            challenge=challenge,
            pubKeyCredParams=pub_key_cred_params,
            timeout=60000,
            attestation=attestation.value,
            authenticatorSelection=authenticator_selection,
            excludeCredentials=exclude_list,
        )

    def verify_registration(
        self,
        user_id: str,
        credential: Dict[str, Any],
        client_data: Dict[str, Any],
    ) -> RegistrationResult:
        try:
            challenge = credential.get("response", {}).get("clientDataJSON")
            if not challenge:
                return RegistrationResult(success=False, error="Missing client data")

            if not self.verify_challenge(user_id, client_data.get("challenge", "")):
                return RegistrationResult(success=False, error="Invalid or expired challenge")

            origin = client_data.get("origin")
            if origin != self.origin:
                logger.warning(f"Origin mismatch: {origin} != {self.origin}")

            if client_data.get("type") != "webauthn.create":
                return RegistrationResult(success=False, error="Invalid client data type")

            cred_id = credential.get("id")
            if not cred_id:
                return RegistrationResult(success=False, error="Missing credential ID")

            attestation_object = credential.get("response", {}).get("attestationObject")
            if not attestation_object:
                return RegistrationResult(success=False, error="Missing attestation object")

            sign_count = 0
            aaguid = None

            public_key = self._extract_public_key(credential)
            if not public_key:
                return RegistrationResult(success=False, error="Could not extract public key")

            user = self._users.get(user_id)
            if user:
                user.credential_id = cred_id
                user.public_key = public_key
                user.sign_count = sign_count
                user.aaguid = aaguid
                self._credentials[cred_id] = user

            return RegistrationResult(
                success=True,
                credential_id=cred_id,
                public_key=public_key,
                sign_count=sign_count,
                aaguid=aaguid,
            )

        except Exception as e:
            logger.error(f"Registration verification failed: {e}")
            return RegistrationResult(success=False, error=str(e))

    def create_authentication_options(
        self,
        user_id: Optional[str] = None,
        credential_ids: Optional[List[str]] = None,
        user_verification: UserVerificationRequirement = UserVerificationRequirement.PREFERRED,
    ) -> CredentialRequestOptions:
        challenge = self.generate_challenge()
        if user_id:
            self.store_challenge(user_id, challenge)

        allow_credentials: List[Dict[str, Any]] = []
        if credential_ids:
            for cred_id in credential_ids:
                user = self._credentials.get(cred_id)
                if user:
                    transports = (
                        [t.value for t in user.transports] if user.transports else ["internal"]
                    )
                    allow_credentials.append(
                        {
                            "type": "public-key",
                            "id": cred_id,
                            "transports": transports,
                        }
                    )
        elif user_id:
            user = self._users.get(user_id)
            if user and user.credential_id:
                allow_credentials.append(
                    {
                        "type": "public-key",
                        "id": user.credential_id,
                        "transports": ["internal", "hybrid"],
                    }
                )

        return CredentialRequestOptions(
            challenge=challenge,
            timeout=60000,
            rpId=self.rp_id,
            allowCredentials=allow_credentials,
            userVerification=user_verification.value,
        )

    def verify_authentication(
        self,
        credential: Dict[str, Any],
        client_data: Dict[str, Any],
    ) -> AuthenticationResult:
        try:
            cred_id = credential.get("id")
            if not cred_id:
                return AuthenticationResult(success=False, error="Missing credential ID")

            user = self._credentials.get(cred_id)
            if not user:
                return AuthenticationResult(success=False, error="Unknown credential")

            if client_data.get("type") != "webauthn.get":
                return AuthenticationResult(success=False, error="Invalid client data type")

            origin = client_data.get("origin")
            if origin != self.origin:
                logger.warning(f"Origin mismatch: {origin} != {self.origin}")

            if not self.verify_challenge(user.user_id, client_data.get("challenge", "")):
                return AuthenticationResult(success=False, error="Invalid or expired challenge")

            auth_data = credential.get("response", {}).get("authenticatorData")
            if not auth_data:
                return AuthenticationResult(success=False, error="Missing authenticator data")

            new_sign_count = credential.get("response", {}).get("signatureCount", 0)

            if new_sign_count <= user.sign_count and user.sign_count != 0:
                logger.warning(
                    f"Possible cloned authenticator: sign_count {new_sign_count} <= {user.sign_count}"
                )
                return AuthenticationResult(
                    success=False, error="Possible authenticator clone detected"
                )

            user.sign_count = new_sign_count

            return AuthenticationResult(
                success=True,
                user_id=user.user_id,
                new_sign_count=new_sign_count,
            )

        except Exception as e:
            logger.error(f"Authentication verification failed: {e}")
            return AuthenticationResult(success=False, error=str(e))

    def _extract_public_key(self, credential: Dict[str, Any]) -> Optional[bytes]:
        try:
            response = credential.get("response", {})
            attestation_obj = response.get("attestationObject")
            if attestation_obj:
                return secrets.token_bytes(32)  # Placeholder
            return None
        except Exception:
            return None

    def register_user(self, user: WebAuthnUser):
        self._users[user.user_id] = user

    def get_user(self, user_id: str) -> Optional[WebAuthnUser]:
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[WebAuthnUser]:
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def remove_credential(self, credential_id: str) -> bool:
        if credential_id in self._credentials:
            user = self._credentials[credential_id]
            user.credential_id = None
            user.public_key = None
            user.sign_count = 0
            del self._credentials[credential_id]
            return True
        return False


webauthn_service = WebAuthnService()
