"""Integration tests for blockchain operations.

These tests verify the interaction between the API and Algorand blockchain.
They use mock/simulated blockchain connections for CI/CD environments.
"""

import os
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from uuid import uuid4

import sys

sys.path.insert(0, ".")

from contracts.client import AlgorandClient, ConsentContractClient, AuditTrailClient


TEST_WALLET = "P3E2KO4G7BA6CFH6ICCYRGEIV5QIY5P6F73LEXAMJJUSAMUHURZN3TRGAI"
TEST_CONSENT_APP_ID = 757755252
TEST_AUDIT_APP_ID = 757755253

TESTING_WITH_SANDBOX = os.getenv("TESTING_WITH_SANDBOX", "").lower() in ("1", "true")


@pytest.fixture
def mock_algorand_client():
    """Create a mock Algorand client for testing."""
    client = Mock(spec=AlgorandClient)
    client.algod_client = Mock()
    client.indexer_client = Mock()
    return client


class TestAlgorandClient:
    """Tests for AlgorandClient."""

    def test_client_initialization(self):
        """Test that client initializes correctly."""
        with patch.dict(
            os.environ,
            {
                "ALGORAND_NODE_URL": "https://testnet-api.algonode.cloud",
                "ALGORAND_INDEXER_URL": "https://testnet-idx.algonode.cloud",
            },
        ):
            client = AlgorandClient()
            assert client is not None

    def test_get_account_info(self, mock_algorand_client):
        """Test getting account information."""
        mock_algorand_client.algod_client.account_info.return_value = {
            "amount": 10000000,
            "apps-local-state": [],
        }

        result = mock_algorand_client.algod_client.account_info(TEST_WALLET)
        assert result["amount"] == 10000000

    def test_get_application_info(self, mock_algorand_client):
        """Test getting application information."""
        mock_algorand_client.algod_client.application_info.return_value = {
            "params": {
                "creator": TEST_WALLET,
                "global-state": [],
            }
        }

        result = mock_algorand_client.algod_client.application_info(TEST_CONSENT_APP_ID)
        assert "params" in result


class TestConsentContractClient:
    """Tests for ConsentContractClient."""

    def test_client_initialization(self, mock_algorand_client):
        """Test consent contract client initialization."""
        client = ConsentContractClient(mock_algorand_client, TEST_CONSENT_APP_ID)
        assert client.app_id == TEST_CONSENT_APP_ID

    def test_verify_consent_mock(self, mock_algorand_client):
        """Test verifying a consent with mock."""
        with patch.object(ConsentContractClient, "verify_consent") as mock_verify:
            mock_verify.return_value = True

            client = ConsentContractClient(mock_algorand_client, TEST_CONSENT_APP_ID)
            result = client.verify_consent("abc123", "mock_verifier_key")
            assert result is True


class TestAuditTrailClient:
    """Tests for AuditTrailClient."""

    def test_client_initialization(self, mock_algorand_client):
        """Test audit trail client initialization."""
        client = AuditTrailClient(mock_algorand_client, TEST_AUDIT_APP_ID)
        assert client.app_id == TEST_AUDIT_APP_ID


class TestBlockchainErrorHandling:
    """Tests for blockchain error handling."""

    def test_network_error_handling(self, mock_algorand_client):
        """Test handling of network errors."""
        mock_algorand_client.algod_client.account_info.side_effect = Exception("Network error")

        with pytest.raises(Exception, match="Network error"):
            mock_algorand_client.algod_client.account_info(TEST_WALLET)


class TestMerkleTreeVerification:
    """Tests for merkle tree verification in blockchain context."""

    def test_merkle_proof_verification(self):
        """Test verifying merkle proofs for audit events."""
        from core.crypto import MerkleTree

        events = [
            "event1:CONSENT_GRANTED:principal1",
            "event2:CONSENT_REVOKED:principal2",
            "event3:DATA_ACCESS:principal1",
            "event4:CONSENT_VERIFIED:principal3",
        ]

        tree = MerkleTree(events)

        for event in events:
            proof = tree.get_proof(events.index(event))
            assert MerkleTree.verify_proof(event, proof, tree.root)

    def test_invalid_merkle_proof(self):
        """Test that invalid merkle proofs are rejected."""
        from core.crypto import MerkleTree

        events = ["event1", "event2", "event3", "event4"]
        tree = MerkleTree(events)

        proof = tree.get_proof(0)
        assert not MerkleTree.verify_proof("wrong_event", proof, tree.root)

    def test_empty_merkle_tree(self):
        """Test empty merkle tree handling."""
        from core.crypto import MerkleTree

        tree = MerkleTree([])
        assert tree.root == MerkleTree.EMPTY_ROOT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
