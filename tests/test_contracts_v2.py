import pytest
from algopy import (
    Account,
    Bytes,
    String,
    UInt64,
    Txn,
    Global,
    arc4,
)
from algopy.arc4 import (
    Address,
    Bool,
    StaticArray,
    arc4_signature,
)

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contracts_v2.consent_registry import ConsentRegistry, ConsentData
from contracts_v2.constants import CONSENT_APP_ID, AUDIT_APP_ID


class TestConsentRegistry:
    @pytest.fixture
    def contract(self):
        return ConsentRegistry()

    @pytest.fixture
    def principal(self):
        return Account()

    @pytest.fixture
    def fiduciary(self):
        return Account()

    @pytest.fixture
    def consent_hash(self):
        return StaticArray[arc4.Byte, literal[32]](Bytes.from_hex("0" * 64))

    @pytest.fixture
    def data_types_hash(self):
        return StaticArray[arc4.Byte, literal[32]](Bytes.from_hex("1" * 64))

    def test_initial_state(self, contract):
        assert contract.total_consents == UInt64(0)
        assert contract.active_consents == UInt64(0)
        assert contract.revoked_consents == UInt64(0)
        assert contract.admin_address == Global.creator_address

    def test_status_constants(self, contract):
        assert contract.STATUS_PENDING == UInt64(0)
        assert contract.STATUS_GRANTED == UInt64(1)
        assert contract.STATUS_REVOKED == UInt64(2)
        assert contract.STATUS_EXPIRED == UInt64(3)
        assert contract.STATUS_MODIFIED == UInt64(4)

    def test_register_consent(
        self,
        contract,
        principal,
        fiduciary,
        consent_hash,
        data_types_hash,
    ):
        purpose = String("Test Purpose")
        expires_at = UInt64(1000000)

        result = contract.register_consent(
            consent_hash=consent_hash,
            principal_address=Address(principal),
            fiduciary_address=Address(fiduciary),
            purpose=purpose,
            data_types_hash=data_types_hash,
            expires_at=expires_at,
        )

        assert result == consent_hash
        assert contract.total_consents == UInt64(1)
        assert contract.active_consents == UInt64(1)

    def test_register_consent_increments_counters(
        self,
        contract,
        principal,
        fiduciary,
        consent_hash,
        data_types_hash,
    ):
        purpose = String("Purpose 1")
        expires_at = UInt64(1000000)

        contract.register_consent(
            consent_hash=consent_hash,
            principal_address=Address(principal),
            fiduciary_address=Address(fiduciary),
            purpose=purpose,
            data_types_hash=data_types_hash,
            expires_at=expires_at,
        )

        assert contract.total_consents == UInt64(1)
        assert contract.active_consents == UInt64(1)

        consent_hash_2 = StaticArray[arc4.Byte, literal[32]](Bytes.from_hex("2" * 64))

        contract.register_consent(
            consent_hash=consent_hash_2,
            principal_address=Address(principal),
            fiduciary_address=Address(fiduciary),
            purpose=String("Purpose 2"),
            data_types_hash=data_types_hash,
            expires_at=expires_at,
        )

        assert contract.total_consents == UInt64(2)
        assert contract.active_consents == UInt64(2)

    def test_revoke_consent(
        self,
        contract,
        principal,
        fiduciary,
        consent_hash,
        data_types_hash,
    ):
        purpose = String("Test Purpose")
        expires_at = UInt64(1000000)

        contract.register_consent(
            consent_hash=consent_hash,
            principal_address=Address(principal),
            fiduciary_address=Address(fiduciary),
            purpose=purpose,
            data_types_hash=data_types_hash,
            expires_at=expires_at,
        )

        result = contract.revoke_consent(consent_hash)

        assert result == Bool(True)
        assert contract.active_consents == UInt64(0)
        assert contract.revoked_consents == UInt64(1)

    def test_revoke_nonexistent_consent_fails(self, contract, consent_hash):
        with pytest.raises(AssertionError):
            contract.revoke_consent(consent_hash)

    def test_modify_consent(
        self,
        contract,
        principal,
        fiduciary,
        consent_hash,
        data_types_hash,
    ):
        purpose = String("Original Purpose")
        expires_at = UInt64(1000000)

        contract.register_consent(
            consent_hash=consent_hash,
            principal_address=Address(principal),
            fiduciary_address=Address(fiduciary),
            purpose=purpose,
            data_types_hash=data_types_hash,
            expires_at=expires_at,
        )

        new_purpose = String("Modified Purpose")
        new_expires_at = UInt64(2000000)

        result = contract.modify_consent(
            consent_hash=consent_hash,
            new_purpose=new_purpose,
            new_expires_at=new_expires_at,
        )

        assert result == Bool(True)

        consent_data = contract.get_consent(consent_hash)
        assert consent_data.purpose == new_purpose
        assert consent_data.expires_at == new_expires_at
        assert consent_data.status == contract.STATUS_MODIFIED

    def test_verify_valid_consent(
        self,
        contract,
        principal,
        fiduciary,
        consent_hash,
        data_types_hash,
    ):
        purpose = String("Test Purpose")
        expires_at = UInt64(10000000)

        contract.register_consent(
            consent_hash=consent_hash,
            principal_address=Address(principal),
            fiduciary_address=Address(fiduciary),
            purpose=purpose,
            data_types_hash=data_types_hash,
            expires_at=expires_at,
        )

        is_valid = contract.verify_consent(consent_hash)
        assert is_valid == Bool(True)

    def test_verify_revoked_consent_fails(
        self,
        contract,
        principal,
        fiduciary,
        consent_hash,
        data_types_hash,
    ):
        purpose = String("Test Purpose")
        expires_at = UInt64(1000000)

        contract.register_consent(
            consent_hash=consent_hash,
            principal_address=Address(principal),
            fiduciary_address=Address(fiduciary),
            purpose=purpose,
            data_types_hash=data_types_hash,
            expires_at=expires_at,
        )

        contract.revoke_consent(consent_hash)

        is_valid = contract.verify_consent(consent_hash)
        assert is_valid == Bool(False)

    def test_verify_nonexistent_consent_fails(self, contract, consent_hash):
        is_valid = contract.verify_consent(consent_hash)
        assert is_valid == Bool(False)

    def test_get_consent(
        self,
        contract,
        principal,
        fiduciary,
        consent_hash,
        data_types_hash,
    ):
        purpose = String("Test Purpose")
        expires_at = UInt64(1000000)

        contract.register_consent(
            consent_hash=consent_hash,
            principal_address=Address(principal),
            fiduciary_address=Address(fiduciary),
            purpose=purpose,
            data_types_hash=data_types_hash,
            expires_at=expires_at,
        )

        consent_data = contract.get_consent(consent_hash)

        assert consent_data.principal_address == Address(principal)
        assert consent_data.fiduciary_address == Address(fiduciary)
        assert consent_data.purpose == purpose
        assert consent_data.status == contract.STATUS_GRANTED
        assert consent_data.expires_at == expires_at

    def test_get_stats(
        self,
        contract,
        principal,
        fiduciary,
        consent_hash,
        data_types_hash,
    ):
        total, active, revoked = contract.get_stats()
        assert total == UInt64(0)
        assert active == UInt64(0)
        assert revoked == UInt64(0)

        purpose = String("Test Purpose")
        expires_at = UInt64(1000000)

        contract.register_consent(
            consent_hash=consent_hash,
            principal_address=Address(principal),
            fiduciary_address=Address(fiduciary),
            purpose=purpose,
            data_types_hash=data_types_hash,
            expires_at=expires_at,
        )

        total, active, revoked = contract.get_stats()
        assert total == UInt64(1)
        assert active == UInt64(1)
        assert revoked == UInt64(0)

    def test_expire_consent(
        self,
        contract,
        principal,
        fiduciary,
        consent_hash,
        data_types_hash,
    ):
        purpose = String("Test Purpose")
        expires_at = UInt64(100)

        contract.register_consent(
            consent_hash=consent_hash,
            principal_address=Address(principal),
            fiduciary_address=Address(fiduciary),
            purpose=purpose,
            data_types_hash=data_types_hash,
            expires_at=expires_at,
        )

        result = contract.expire_consent(consent_hash)
        assert result == Bool(True)
        assert contract.active_consents == UInt64(0)


class TestConsentDataStruct:
    def test_consent_data_structure(self):
        data = ConsentData()

        assert hasattr(data, "principal_address")
        assert hasattr(data, "fiduciary_address")
        assert hasattr(data, "purpose")
        assert hasattr(data, "data_types_hash")
        assert hasattr(data, "status")
        assert hasattr(data, "granted_at")
        assert hasattr(data, "expires_at")
        assert hasattr(data, "revoked_at")
