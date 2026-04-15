from algopy import ARC4Contract, UInt64, Bytes, String, arc4, Global, Txn, itxn, Asset, op, Account
from algopy.arc4 import abimethod, Struct, DynamicArray, StaticArray, Address, Bool


class ConsentData(Struct):
    principal_address: Address
    fiduciary_address: Address
    purpose: String
    data_types_hash: StaticArray[arc4.Byte, literal[32]]
    status: UInt64
    granted_at: UInt64
    expires_at: UInt64
    revoked_at: UInt64


class ConsentRegistry(ARC4Contract):
    STATUS_PENDING = UInt64(0)
    STATUS_GRANTED = UInt64(1)
    STATUS_REVOKED = UInt64(2)
    STATUS_EXPIRED = UInt64(3)
    STATUS_MODIFIED = UInt64(4)

    def __init__(self) -> None:
        self.total_consents = UInt64(0)
        self.active_consents = UInt64(0)
        self.revoked_consents = UInt64(0)
        self.admin_address = Global.creator_address

    @abimethod(allow_actions=["NoOp"])
    def register_consent(
        self,
        consent_hash: StaticArray[arc4.Byte, literal[32]],
        principal_address: Address,
        fiduciary_address: Address,
        purpose: String,
        data_types_hash: StaticArray[arc4.Byte, literal[32]],
        expires_at: UInt64,
    ) -> StaticArray[arc4.Byte, literal[32]]:
        assert Txn.sender == self.admin_address or Txn.sender == principal_address.native, (
            "Unauthorized"
        )

        consent_data = ConsentData(
            principal_address=principal_address,
            fiduciary_address=fiduciary_address,
            purpose=purpose,
            data_types_hash=data_types_hash,
            status=self.STATUS_GRANTED,
            granted_at=Global.round,
            expires_at=expires_at,
            revoked_at=UInt64(0),
        )

        self.consent_box = op.Box(consent_hash.bytes, consent_data)

        self.total_consents += UInt64(1)
        self.active_consents += UInt64(1)

        return consent_hash

    @abimethod()
    def revoke_consent(
        self,
        consent_hash: StaticArray[arc4.Byte, literal[32]],
    ) -> Bool:
        consent_data = op.Box.get(consent_hash.bytes)
        assert consent_data, "Consent not found"

        stored_data = ConsentData.from_bytes(consent_data)
        assert Txn.sender == stored_data.principal_address.native, "Only principal can revoke"
        assert stored_data.status == self.STATUS_GRANTED, "Consent not active"

        stored_data.status = self.STATUS_REVOKED
        stored_data.revoked_at = Global.round

        op.Box.replace(consent_hash.bytes, UInt64(0), stored_data.bytes)

        self.active_consents -= UInt64(1)
        self.revoked_consents += UInt64(1)

        return Bool(True)

    @abimethod()
    def modify_consent(
        self,
        consent_hash: StaticArray[arc4.Byte, literal[32]],
        new_purpose: String,
        new_expires_at: UInt64,
    ) -> Bool:
        consent_data = op.Box.get(consent_hash.bytes)
        assert consent_data, "Consent not found"

        stored_data = ConsentData.from_bytes(consent_data)
        assert Txn.sender == stored_data.principal_address.native, "Only principal can modify"
        assert stored_data.status != self.STATUS_REVOKED, "Cannot modify revoked consent"

        if new_purpose.length > UInt64(0):
            stored_data.purpose = new_purpose
        if new_expires_at > UInt64(0):
            stored_data.expires_at = new_expires_at

        stored_data.status = self.STATUS_MODIFIED

        op.Box.replace(consent_hash.bytes, UInt64(0), stored_data.bytes)

        return Bool(True)

    @abimethod(readonly=True)
    def verify_consent(
        self,
        consent_hash: StaticArray[arc4.Byte, literal[32]],
    ) -> Bool:
        consent_data = op.Box.get(consent_hash.bytes)
        if not consent_data:
            return Bool(False)

        stored_data = ConsentData.from_bytes(consent_data)

        if stored_data.status != self.STATUS_GRANTED:
            return Bool(False)

        if stored_data.expires_at > UInt64(0) and Global.round > stored_data.expires_at:
            return Bool(False)

        return Bool(True)

    @abimethod(readonly=True)
    def get_consent(
        self,
        consent_hash: StaticArray[arc4.Byte, literal[32]],
    ) -> ConsentData:
        consent_data = op.Box.get(consent_hash.bytes)
        assert consent_data, "Consent not found"
        return ConsentData.from_bytes(consent_data)

    @abimethod()
    def expire_consent(
        self,
        consent_hash: StaticArray[arc4.Byte, literal[32]],
    ) -> Bool:
        consent_data = op.Box.get(consent_hash.bytes)
        assert consent_data, "Consent not found"

        stored_data = ConsentData.from_bytes(consent_data)
        assert stored_data.status == self.STATUS_GRANTED, "Consent not active"
        assert Global.round > stored_data.expires_at, "Consent not yet expired"

        stored_data.status = self.STATUS_EXPIRED

        op.Box.replace(consent_hash.bytes, UInt64(0), stored_data.bytes)

        self.active_consents -= UInt64(1)

        return Bool(True)

    @abimethod(readonly=True)
    def get_stats(self) -> tuple[UInt64, UInt64, UInt64]:
        return (self.total_consents, self.active_consents, self.revoked_consents)
