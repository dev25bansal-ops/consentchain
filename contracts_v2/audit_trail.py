from algopy import ARC4Contract, UInt64, Bytes, String, arc4, Global, Txn, op
from algopy.arc4 import abimethod, Struct, DynamicArray, StaticArray, Address, Bool


class AuditEvent(Struct):
    event_hash: StaticArray[arc4.Byte, literal[32]]
    event_type: UInt64
    consent_hash: StaticArray[arc4.Byte, literal[32]]
    actor: Address
    timestamp: UInt64
    previous_status: UInt64
    new_status: UInt64
    merkle_proof: StaticArray[arc4.Byte, literal[32]]


class AuditTrail(ARC4Contract):
    EVENT_GRANTED = UInt64(1)
    EVENT_REVOKED = UInt64(2)
    EVENT_MODIFIED = UInt64(3)
    EVENT_EXPIRED = UInt64(4)
    EVENT_ACCESSED = UInt64(5)

    def __init__(self) -> None:
        self.event_counter = UInt64(0)
        self.merkle_root = StaticArray[arc4.Byte, literal[32]](Bytes(32))
        self.last_event_hash = StaticArray[arc4.Byte, literal[32]](Bytes(32))
        self.admin_address = Global.creator_address
        self.registry_app_id = UInt64(0)

    @abimethod(allow_actions=["NoOp"])
    def set_registry(self, registry_app_id: UInt64) -> Bool:
        assert Txn.sender == self.admin_address, "Only admin can set registry"
        self.registry_app_id = registry_app_id
        return Bool(True)

    @abimethod(allow_actions=["NoOp"])
    def log_event(
        self,
        event_hash: StaticArray[arc4.Byte, literal[32]],
        event_type: UInt64,
        consent_hash: StaticArray[arc4.Byte, literal[32]],
        actor: Address,
        previous_status: UInt64,
        new_status: UInt64,
    ) -> Bool:
        event = AuditEvent(
            event_hash=event_hash,
            event_type=event_type,
            consent_hash=consent_hash,
            actor=actor,
            timestamp=Global.round,
            previous_status=previous_status,
            new_status=new_status,
            merkle_proof=self.last_event_hash,
        )

        op.Box.put(event_hash.bytes, event.bytes)

        self.last_event_hash = event_hash
        self.event_counter += UInt64(1)

        return Bool(True)

    @abimethod(allow_actions=["NoOp"])
    def batch_log_events(
        self,
        merkle_root: StaticArray[arc4.Byte, literal[32]],
        event_count: UInt64,
        last_event_hash: StaticArray[arc4.Byte, literal[32]],
    ) -> Bool:
        self.merkle_root = merkle_root
        self.event_counter += event_count
        self.last_event_hash = last_event_hash
        return Bool(True)

    @abimethod(readonly=True)
    def get_event(
        self,
        event_hash: StaticArray[arc4.Byte, literal[32]],
    ) -> AuditEvent:
        event_data = op.Box.get(event_hash.bytes)
        assert event_data, "Event not found"
        return AuditEvent.from_bytes(event_data)

    @abimethod(readonly=True)
    def get_merkle_root(self) -> StaticArray[arc4.Byte, literal[32]]:
        return self.merkle_root

    @abimethod(readonly=True)
    def get_event_count(self) -> UInt64:
        return self.event_counter

    @abimethod(readonly=True)
    def verify_event(
        self,
        event_hash: StaticArray[arc4.Byte, literal[32]],
    ) -> Bool:
        event_data = op.Box.get(event_hash.bytes)
        return Bool(event_data != Bytes())
