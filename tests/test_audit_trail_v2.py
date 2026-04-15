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
)

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contracts_v2.audit_trail import AuditTrail, AuditEvent


class TestAuditTrail:
    @pytest.fixture
    def contract(self):
        return AuditTrail()

    @pytest.fixture
    def actor(self):
        return Account()

    @pytest.fixture
    def event_hash(self):
        return StaticArray[arc4.Byte, literal[32]](Bytes.from_hex("0" * 64))

    @pytest.fixture
    def consent_hash(self):
        return StaticArray[arc4.Byte, literal[32]](Bytes.from_hex("1" * 64))

    def test_initial_state(self, contract):
        assert contract.event_counter == UInt64(0)
        assert contract.merkle_root == StaticArray[arc4.Byte, literal[32]](Bytes(32))
        assert contract.last_event_hash == StaticArray[arc4.Byte, literal[32]](Bytes(32))
        assert contract.admin_address == Global.creator_address
        assert contract.registry_app_id == UInt64(0)

    def test_event_type_constants(self, contract):
        assert contract.EVENT_GRANTED == UInt64(1)
        assert contract.EVENT_REVOKED == UInt64(2)
        assert contract.EVENT_MODIFIED == UInt64(3)
        assert contract.EVENT_EXPIRED == UInt64(4)
        assert contract.EVENT_ACCESSED == UInt64(5)

    def test_set_registry(self, contract):
        registry_app_id = UInt64(12345)
        result = contract.set_registry(registry_app_id)

        assert result == Bool(True)
        assert contract.registry_app_id == registry_app_id

    def test_log_event(
        self,
        contract,
        actor,
        event_hash,
        consent_hash,
    ):
        event_type = UInt64(1)  # EVENT_GRANTED
        previous_status = UInt64(0)
        new_status = UInt64(1)

        result = contract.log_event(
            event_hash=event_hash,
            event_type=event_type,
            consent_hash=consent_hash,
            actor=Address(actor),
            previous_status=previous_status,
            new_status=new_status,
        )

        assert result == Bool(True)
        assert contract.event_counter == UInt64(1)
        assert contract.last_event_hash == event_hash

    def test_log_multiple_events(
        self,
        contract,
        actor,
        event_hash,
        consent_hash,
    ):
        event_type = UInt64(1)
        previous_status = UInt64(0)
        new_status = UInt64(1)

        contract.log_event(
            event_hash=event_hash,
            event_type=event_type,
            consent_hash=consent_hash,
            actor=Address(actor),
            previous_status=previous_status,
            new_status=new_status,
        )

        event_hash_2 = StaticArray[arc4.Byte, literal[32]](Bytes.from_hex("2" * 64))
        event_type_2 = UInt64(2)  # EVENT_REVOKED

        contract.log_event(
            event_hash=event_hash_2,
            event_type=event_type_2,
            consent_hash=consent_hash,
            actor=Address(actor),
            previous_status=UInt64(1),
            new_status=UInt64(2),
        )

        assert contract.event_counter == UInt64(2)
        assert contract.last_event_hash == event_hash_2

    def test_batch_log_events(self, contract):
        merkle_root = StaticArray[arc4.Byte, literal[32]](Bytes.from_hex("a" * 64))
        event_count = UInt64(10)
        last_event_hash = StaticArray[arc4.Byte, literal[32]](Bytes.from_hex("b" * 64))

        result = contract.batch_log_events(
            merkle_root=merkle_root,
            event_count=event_count,
            last_event_hash=last_event_hash,
        )

        assert result == Bool(True)
        assert contract.merkle_root == merkle_root
        assert contract.event_counter == UInt64(10)
        assert contract.last_event_hash == last_event_hash

    def test_get_event(
        self,
        contract,
        actor,
        event_hash,
        consent_hash,
    ):
        event_type = UInt64(1)
        previous_status = UInt64(0)
        new_status = UInt64(1)

        contract.log_event(
            event_hash=event_hash,
            event_type=event_type,
            consent_hash=consent_hash,
            actor=Address(actor),
            previous_status=previous_status,
            new_status=new_status,
        )

        event_data = contract.get_event(event_hash)

        assert event_data.event_hash == event_hash
        assert event_data.event_type == event_type
        assert event_data.consent_hash == consent_hash
        assert event_data.actor == Address(actor)
        assert event_data.previous_status == previous_status
        assert event_data.new_status == new_status

    def test_get_event_not_found_fails(self, contract, event_hash):
        with pytest.raises(AssertionError):
            contract.get_event(event_hash)

    def test_get_merkle_root(self, contract):
        merkle_root = contract.get_merkle_root()
        assert merkle_root == StaticArray[arc4.Byte, literal[32]](Bytes(32))

    def test_get_merkle_root_after_batch_log(self, contract):
        merkle_root_value = StaticArray[arc4.Byte, literal[32]](Bytes.from_hex("a" * 64))

        contract.batch_log_events(
            merkle_root=merkle_root_value,
            event_count=UInt64(5),
            last_event_hash=StaticArray[arc4.Byte, literal[32]](Bytes.from_hex("b" * 64)),
        )

        merkle_root = contract.get_merkle_root()
        assert merkle_root == merkle_root_value

    def test_get_event_count(self, contract):
        count = contract.get_event_count()
        assert count == UInt64(0)

    def test_get_event_count_after_logging(
        self,
        contract,
        actor,
        event_hash,
        consent_hash,
    ):
        contract.log_event(
            event_hash=event_hash,
            event_type=UInt64(1),
            consent_hash=consent_hash,
            actor=Address(actor),
            previous_status=UInt64(0),
            new_status=UInt64(1),
        )

        count = contract.get_event_count()
        assert count == UInt64(1)

    def test_verify_event_exists(
        self,
        contract,
        actor,
        event_hash,
        consent_hash,
    ):
        contract.log_event(
            event_hash=event_hash,
            event_type=UInt64(1),
            consent_hash=consent_hash,
            actor=Address(actor),
            previous_status=UInt64(0),
            new_status=UInt64(1),
        )

        is_valid = contract.verify_event(event_hash)
        assert is_valid == Bool(True)

    def test_verify_event_not_exists(self, contract, event_hash):
        is_valid = contract.verify_event(event_hash)
        assert is_valid == Bool(False)


class TestAuditEventStruct:
    def test_audit_event_structure(self):
        event = AuditEvent()

        assert hasattr(event, "event_hash")
        assert hasattr(event, "event_type")
        assert hasattr(event, "consent_hash")
        assert hasattr(event, "actor")
        assert hasattr(event, "timestamp")
        assert hasattr(event, "previous_status")
        assert hasattr(event, "new_status")
        assert hasattr(event, "merkle_proof")
