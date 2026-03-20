import hashlib
import json
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
import base64


class CryptoUtils:
    @staticmethod
    def sha256(data: str | bytes) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def sha512(data: str | bytes) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha512(data).hexdigest()

    @staticmethod
    def keccak256(data: str | bytes) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        from hashlib import sha3_256

        return sha3_256(data).hexdigest()

    @staticmethod
    def generate_consent_hash(
        principal_id: str,
        fiduciary_id: str,
        purpose: str,
        data_types: list,
        timestamp: datetime,
        nonce: Optional[str] = None,
    ) -> str:
        if nonce is None:
            nonce = secrets.token_hex(16)

        consent_data = {
            "principal_id": str(principal_id),
            "fiduciary_id": str(fiduciary_id),
            "purpose": purpose,
            "data_types": sorted(data_types),
            "timestamp": timestamp.isoformat(),
            "nonce": nonce,
        }

        canonical_json = json.dumps(consent_data, sort_keys=True, separators=(",", ":"))
        return CryptoUtils.sha256(canonical_json)

    @staticmethod
    def generate_audit_hash(
        event_type: str,
        consent_id: str,
        timestamp: datetime,
        previous_hash: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        audit_data = {
            "event_type": event_type,
            "consent_id": str(consent_id),
            "timestamp": timestamp.isoformat(),
            "previous_hash": previous_hash or "0" * 64,
            "metadata": metadata or {},
        }

        canonical_json = json.dumps(audit_data, sort_keys=True, separators=(",", ":"))
        return CryptoUtils.sha256(canonical_json)

    @staticmethod
    def hash_email(email: str) -> str:
        normalized = email.lower().strip()
        return CryptoUtils.sha256(f"email:{normalized}")

    @staticmethod
    def hash_phone(phone: str) -> str:
        import re

        normalized = re.sub(r"[^\d+]", "", phone)
        return CryptoUtils.sha256(f"phone:{normalized}")

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        return CryptoUtils.sha256(f"apikey:{api_key}")

    @staticmethod
    def generate_api_key() -> str:
        raw_key = secrets.token_urlsafe(32)
        return f"cc_{raw_key}"

    @staticmethod
    def generate_nonce() -> str:
        return secrets.token_hex(16)


class SignatureManager:
    def __init__(self):
        self._private_key: Optional[ed25519.Ed25519PrivateKey] = None
        self._public_key: Optional[ed25519.Ed25519PublicKey] = None

    @classmethod
    def generate_keypair(cls) -> tuple:
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        return private_key, public_key

    @classmethod
    def sign_message(cls, private_key: ed25519.Ed25519PrivateKey, message: str | bytes) -> str:
        if isinstance(message, str):
            message = message.encode("utf-8")
        signature = private_key.sign(message)
        return base64.b64encode(signature).decode("utf-8")

    @classmethod
    def verify_signature(
        cls,
        public_key: ed25519.Ed25519PublicKey,
        message: str | bytes,
        signature: str,
    ) -> bool:
        try:
            if isinstance(message, str):
                message = message.encode("utf-8")
            sig_bytes = base64.b64decode(signature)
            public_key.verify(sig_bytes, message)
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False

    @classmethod
    def export_private_key(
        cls, private_key: ed25519.Ed25519PrivateKey, password: Optional[bytes] = None
    ) -> str:
        encryption = serialization.NoEncryption()
        if password:
            encryption = serialization.BestAvailableEncryption(password)

        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption,
        )
        return pem.decode("utf-8")

    @classmethod
    def export_public_key(cls, public_key: ed25519.Ed25519PublicKey) -> str:
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return pem.decode("utf-8")

    @classmethod
    def load_private_key(
        cls, pem_data: str, password: Optional[bytes] = None
    ) -> ed25519.Ed25519PrivateKey:
        private_key = serialization.load_pem_private_key(
            pem_data.encode("utf-8"),
            password=password,
            backend=default_backend(),
        )
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise ValueError("Invalid key type, expected Ed25519")
        return private_key

    @classmethod
    def load_public_key(cls, pem_data: str) -> ed25519.Ed25519PublicKey:
        public_key = serialization.load_pem_public_key(
            pem_data.encode("utf-8"),
            backend=default_backend(),
        )
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise ValueError("Invalid key type, expected Ed25519")
        return public_key


class MerkleTree:
    def __init__(self, leaves: list):
        self.leaves = [CryptoUtils.sha256(str(leaf)) for leaf in leaves]
        self.tree = self._build_tree(self.leaves)

    def _build_tree(self, leaves: list) -> list:
        if len(leaves) == 1:
            return [leaves]

        tree = [leaves]
        current_level = leaves

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else current_level[i]
                combined = CryptoUtils.sha256(left + right)
                next_level.append(combined)
            tree.append(next_level)
            current_level = next_level

        return tree

    @property
    def root(self) -> str:
        return self.tree[-1][0] if self.tree else "0" * 64

    def get_proof(self, leaf_index: int) -> list:
        if leaf_index >= len(self.leaves):
            raise IndexError("Leaf index out of range")

        proof = []
        index = leaf_index

        for level in self.tree[:-1]:
            sibling_index = index ^ 1
            if sibling_index < len(level):
                proof.append(
                    {
                        "hash": level[sibling_index],
                        "position": "left" if sibling_index < index else "right",
                    }
                )
            index = index // 2

        return proof

    @staticmethod
    def verify_proof(leaf: str, proof: list, root: str) -> bool:
        current_hash = CryptoUtils.sha256(leaf)

        for step in proof:
            sibling_hash = step["hash"]
            if step["position"] == "left":
                current_hash = CryptoUtils.sha256(sibling_hash + current_hash)
            else:
                current_hash = CryptoUtils.sha256(current_hash + sibling_hash)

        return current_hash == root


class DPDPComplianceValidator:
    SENSITIVE_DATA_TYPES = {
        "FINANCIAL_DATA",
        "HEALTH_DATA",
        "BIOMETRIC_DATA",
        "SENSITIVE_DATA",
    }

    @classmethod
    def validate_consent_purpose(cls, purpose: str, data_types: list) -> tuple[bool, list]:
        violations = []

        has_sensitive = any(dt in cls.SENSITIVE_DATA_TYPES for dt in data_types)

        if has_sensitive:
            if purpose in ["MARKETING", "ANALYTICS"]:
                violations.append(
                    f"Sensitive data cannot be used for {purpose} without explicit consent"
                )

        if purpose == "THIRD_PARTY_SHARING":
            violations.append("Third-party sharing requires explicit consent mention")

        return len(violations) == 0, violations

    @classmethod
    def validate_consent_duration(cls, duration_days: int, purpose: str) -> tuple[bool, str]:
        if duration_days < 1:
            return False, "Duration must be at least 1 day"

        max_durations = {
            "MARKETING": 90,
            "ANALYTICS": 180,
            "SERVICE_DELIVERY": 365,
            "THIRD_PARTY_SHARING": 90,
            "RESEARCH": 365,
            "COMPLIANCE": 365,
            "PAYMENT_PROCESSING": 365,
        }

        max_days = max_durations.get(purpose, 365)
        if duration_days > max_days:
            return False, f"Duration exceeds maximum allowed ({max_days} days) for {purpose}"

        return True, ""

    @classmethod
    def check_revocation_rights(cls, consent_data: dict) -> dict:
        return {
            "can_revoke": True,
            "revocation_effective_immediately": True,
            "data_deletion_required": True,
            "deletion_deadline_days": 30,
            "third_party_notification_required": True,
        }

    @classmethod
    def generate_compliance_checklist(cls, fiduciary_data: dict) -> list:
        return [
            {"item": "Consent request clearly states purpose", "required": True},
            {"item": "Data categories explicitly listed", "required": True},
            {"item": "Consent duration specified", "required": True},
            {"item": "Right to revoke clearly communicated", "required": True},
            {"item": "Grievance redressal mechanism provided", "required": True},
            {"item": "Data retention policy disclosed", "required": True},
            {"item": "Third-party sharing disclosure", "required": True},
            {"item": "Consent withdrawal mechanism available", "required": True},
        ]
