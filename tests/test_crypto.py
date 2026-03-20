import pytest
from datetime import datetime, timedelta
from uuid import uuid4

import sys

sys.path.insert(0, ".")

from core.crypto import CryptoUtils, MerkleTree, SignatureManager, DPDPComplianceValidator


class TestCryptoUtils:
    def test_sha256_hash(self):
        data = "test_data"
        hash_result = CryptoUtils.sha256(data)
        assert len(hash_result) == 64
        assert hash_result == CryptoUtils.sha256(data)

    def test_sha512_hash(self):
        data = "test_data"
        hash_result = CryptoUtils.sha512(data)
        assert len(hash_result) == 128

    def test_generate_consent_hash(self):
        principal_id = str(uuid4())
        fiduciary_id = str(uuid4())
        purpose = "MARKETING"
        data_types = ["PERSONAL_INFO", "CONTACT_INFO"]
        timestamp = datetime.utcnow()

        consent_hash = CryptoUtils.generate_consent_hash(
            principal_id, fiduciary_id, purpose, data_types, timestamp
        )

        assert len(consent_hash) == 64

        same_hash = CryptoUtils.generate_consent_hash(
            principal_id, fiduciary_id, purpose, data_types, timestamp
        )
        assert consent_hash == same_hash

    def test_generate_consent_hash_different_nonce(self):
        principal_id = str(uuid4())
        fiduciary_id = str(uuid4())
        purpose = "MARKETING"
        data_types = ["PERSONAL_INFO"]
        timestamp = datetime.utcnow()

        hash1 = CryptoUtils.generate_consent_hash(
            principal_id, fiduciary_id, purpose, data_types, timestamp, "nonce1"
        )
        hash2 = CryptoUtils.generate_consent_hash(
            principal_id, fiduciary_id, purpose, data_types, timestamp, "nonce2"
        )

        assert hash1 != hash2

    def test_hash_email_normalization(self):
        hash1 = CryptoUtils.hash_email("Test@Example.com")
        hash2 = CryptoUtils.hash_email("test@example.com")
        hash3 = CryptoUtils.hash_email("  test@example.com  ")

        assert hash1 == hash2
        assert hash2 == hash3
        assert len(hash1) == 64

    def test_hash_phone_normalization(self):
        hash1 = CryptoUtils.hash_phone("+91 98765 43210")
        hash2 = CryptoUtils.hash_phone("+919876543210")
        hash3 = CryptoUtils.hash_phone("98765-43210")

        assert len(hash1) == 64

    def test_generate_api_key(self):
        api_key = CryptoUtils.generate_api_key()
        assert api_key.startswith("cc_")
        assert len(api_key) > 20


class TestMerkleTree:
    def test_empty_tree(self):
        tree = MerkleTree([])
        assert tree.root == "0" * 64

    def test_single_leaf(self):
        tree = MerkleTree(["data1"])
        assert len(tree.root) == 64
        assert tree.root == CryptoUtils.sha256("data1")

    def test_multiple_leaves(self):
        leaves = ["data1", "data2", "data3", "data4"]
        tree = MerkleTree(leaves)

        assert len(tree.root) == 64

        proof = tree.get_proof(0)
        assert MerkleTree.verify_proof("data1", proof, tree.root)

    def test_proof_verification(self):
        leaves = ["a", "b", "c", "d"]
        tree = MerkleTree(leaves)

        for i, leaf in enumerate(leaves):
            proof = tree.get_proof(i)
            assert MerkleTree.verify_proof(leaf, proof, tree.root)

    def test_invalid_proof(self):
        leaves = ["a", "b", "c", "d"]
        tree = MerkleTree(leaves)

        proof = tree.get_proof(0)
        assert not MerkleTree.verify_proof("wrong_data", proof, tree.root)


class TestSignatureManager:
    def test_keypair_generation(self):
        private_key, public_key = SignatureManager.generate_keypair()
        assert private_key is not None
        assert public_key is not None

    def test_sign_and_verify(self):
        private_key, public_key = SignatureManager.generate_keypair()
        message = "test_message"

        signature = SignatureManager.sign_message(private_key, message)
        assert len(signature) > 0

        assert SignatureManager.verify_signature(public_key, message, signature)

    def test_invalid_signature(self):
        private_key, public_key = SignatureManager.generate_keypair()
        signature = SignatureManager.sign_message(private_key, "original_message")

        assert not SignatureManager.verify_signature(public_key, "different_message", signature)

    def test_key_export_import(self):
        private_key, public_key = SignatureManager.generate_keypair()

        private_pem = SignatureManager.export_private_key(private_key)
        public_pem = SignatureManager.export_public_key(public_key)

        assert "BEGIN PRIVATE KEY" in private_pem
        assert "BEGIN PUBLIC KEY" in public_pem

        loaded_private = SignatureManager.load_private_key(private_pem)
        loaded_public = SignatureManager.load_public_key(public_pem)

        message = "test"
        signature = SignatureManager.sign_message(loaded_private, message)
        assert SignatureManager.verify_signature(loaded_public, message, signature)


class TestDPDPComplianceValidator:
    def test_validate_consent_purpose_valid(self):
        is_valid, violations = DPDPComplianceValidator.validate_consent_purpose(
            "SERVICE_DELIVERY", ["PERSONAL_INFO", "CONTACT_INFO"]
        )
        assert is_valid
        assert len(violations) == 0

    def test_validate_consent_purpose_sensitive_data_marketing(self):
        is_valid, violations = DPDPComplianceValidator.validate_consent_purpose(
            "MARKETING", ["FINANCIAL_DATA"]
        )
        assert not is_valid
        assert len(violations) > 0

    def test_validate_consent_duration_valid(self):
        is_valid, error = DPDPComplianceValidator.validate_consent_duration(90, "MARKETING")
        assert is_valid
        assert error == ""

    def test_validate_consent_duration_too_long(self):
        is_valid, error = DPDPComplianceValidator.validate_consent_duration(365, "MARKETING")
        assert not is_valid
        assert "exceeds maximum" in error.lower()

    def test_validate_consent_duration_negative(self):
        is_valid, error = DPDPComplianceValidator.validate_consent_duration(-1, "MARKETING")
        assert not is_valid

    def test_check_revocation_rights(self):
        rights = DPDPComplianceValidator.check_revocation_rights({})
        assert rights["can_revoke"] is True
        assert rights["revocation_effective_immediately"] is True
        assert rights["data_deletion_required"] is True

    def test_generate_compliance_checklist(self):
        checklist = DPDPComplianceValidator.generate_compliance_checklist({})
        assert len(checklist) > 0

        for item in checklist:
            assert "item" in item
            assert "required" in item


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
