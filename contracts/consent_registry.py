from pyteal import *
from typing import Final


class ConsentRegistry:
    VERSION: Final[int] = 1

    class LocalState:
        principal_address = Bytes("principal")
        fiduciary_address = Bytes("fiduciary")
        purpose = Bytes("purpose")
        data_types_hash = Bytes("data_hash")
        status = Bytes("status")
        granted_at = Bytes("granted_at")
        expires_at = Bytes("expires_at")
        consent_hash = Bytes("consent_hash")
        revoked_at = Bytes("revoked_at")

    class GlobalState:
        total_consents = Bytes("total_consents")
        active_consents = Bytes("active_consents")
        revoked_consents = Bytes("revoked_consents")
        admin_address = Bytes("admin")
        version = Bytes("version")
        registry_name = Bytes("ConsentChain Registry")

    class AppArgs:
        ACTION_REGISTER = Bytes("register")
        ACTION_REVOKE = Bytes("revoke")
        ACTION_MODIFY = Bytes("modify")
        ACTION_VERIFY = Bytes("verify")
        ACTION_QUERY = Bytes("query")

    class StatusCodes:
        STATUS_PENDING = Int(0)
        STATUS_GRANTED = Int(1)
        STATUS_REVOKED = Int(2)
        STATUS_EXPIRED = Int(3)
        STATUS_MODIFIED = Int(4)

    @staticmethod
    def approval_program():
        action = Txn.application_args[0]

        register_consent = Seq(
            [
                Assert(Txn.application_args.length() >= Int(6)),
                App.localPut(
                    Txn.sender(),
                    ConsentRegistry.LocalState.principal_address,
                    Txn.application_args[1],
                ),
                App.localPut(
                    Txn.sender(),
                    ConsentRegistry.LocalState.fiduciary_address,
                    Txn.application_args[2],
                ),
                App.localPut(
                    Txn.sender(), ConsentRegistry.LocalState.purpose, Txn.application_args[3]
                ),
                App.localPut(
                    Txn.sender(),
                    ConsentRegistry.LocalState.data_types_hash,
                    Txn.application_args[4],
                ),
                App.localPut(
                    Txn.sender(), ConsentRegistry.LocalState.consent_hash, Txn.application_args[5]
                ),
                App.localPut(
                    Txn.sender(),
                    ConsentRegistry.LocalState.status,
                    Itob(ConsentRegistry.StatusCodes.STATUS_GRANTED),
                ),
                App.localPut(
                    Txn.sender(), ConsentRegistry.LocalState.granted_at, Itob(Global.round())
                ),
                If(Txn.application_args.length() > Int(6)).Then(
                    App.localPut(
                        Txn.sender(), ConsentRegistry.LocalState.expires_at, Txn.application_args[6]
                    )
                ),
                App.globalPut(
                    ConsentRegistry.GlobalState.total_consents,
                    App.globalGet(ConsentRegistry.GlobalState.total_consents) + Int(1),
                ),
                App.globalPut(
                    ConsentRegistry.GlobalState.active_consents,
                    App.globalGet(ConsentRegistry.GlobalState.active_consents) + Int(1),
                ),
                Approve(),
            ]
        )

        revoke_consent = Seq(
            [
                Assert(
                    Txn.sender()
                    == App.localGet(Txn.sender(), ConsentRegistry.LocalState.principal_address)
                ),
                App.localPut(
                    Txn.sender(),
                    ConsentRegistry.LocalState.status,
                    Itob(ConsentRegistry.StatusCodes.STATUS_REVOKED),
                ),
                App.localPut(
                    Txn.sender(), ConsentRegistry.LocalState.revoked_at, Itob(Global.round())
                ),
                App.globalPut(
                    ConsentRegistry.GlobalState.active_consents,
                    App.globalGet(ConsentRegistry.GlobalState.active_consents) - Int(1),
                ),
                App.globalPut(
                    ConsentRegistry.GlobalState.revoked_consents,
                    App.globalGet(ConsentRegistry.GlobalState.revoked_consents) + Int(1),
                ),
                Approve(),
            ]
        )

        modify_consent = Seq(
            [
                Assert(Txn.application_args.length() >= Int(3)),
                Assert(
                    Txn.sender()
                    == App.localGet(Txn.sender(), ConsentRegistry.LocalState.principal_address)
                ),
                If(Txn.application_args[1] != Bytes("")).Then(
                    App.localPut(
                        Txn.sender(), ConsentRegistry.LocalState.purpose, Txn.application_args[1]
                    )
                ),
                If(Txn.application_args.length() > Int(2)).Then(
                    If(Txn.application_args[2] != Bytes("")).Then(
                        App.localPut(
                            Txn.sender(),
                            ConsentRegistry.LocalState.expires_at,
                            Txn.application_args[2],
                        )
                    )
                ),
                App.localPut(
                    Txn.sender(),
                    ConsentRegistry.LocalState.status,
                    Itob(ConsentRegistry.StatusCodes.STATUS_MODIFIED),
                ),
                Approve(),
            ]
        )

        verify_consent = Seq(
            [
                Assert(Txn.application_args.length() >= Int(2)),
                If(
                    App.localGet(Txn.sender(), ConsentRegistry.LocalState.status)
                    == Itob(ConsentRegistry.StatusCodes.STATUS_GRANTED)
                )
                .Then(Approve())
                .Else(Reject()),
            ]
        )

        query_status = Seq([Approve()])

        program = Cond(
            [action == ConsentRegistry.AppArgs.ACTION_REGISTER, register_consent],
            [action == ConsentRegistry.AppArgs.ACTION_REVOKE, revoke_consent],
            [action == ConsentRegistry.AppArgs.ACTION_MODIFY, modify_consent],
            [action == ConsentRegistry.AppArgs.ACTION_VERIFY, verify_consent],
            [action == ConsentRegistry.AppArgs.ACTION_QUERY, query_status],
        )

        return program

    @staticmethod
    def clear_state_program():
        return Seq(
            [
                App.globalPut(
                    ConsentRegistry.GlobalState.total_consents,
                    App.globalGet(ConsentRegistry.GlobalState.total_consents) - Int(1),
                ),
                If(
                    App.localGet(Txn.sender(), ConsentRegistry.LocalState.status)
                    == Itob(ConsentRegistry.StatusCodes.STATUS_GRANTED)
                ).Then(
                    App.globalPut(
                        ConsentRegistry.GlobalState.active_consents,
                        App.globalGet(ConsentRegistry.GlobalState.active_consents) - Int(1),
                    )
                ),
                Approve(),
            ]
        )

    @staticmethod
    def get_approval_program():
        return compileTeal(ConsentRegistry.approval_program(), Mode.Application, version=8)

    @staticmethod
    def get_clear_state_program():
        return compileTeal(ConsentRegistry.clear_state_program(), Mode.Application, version=8)


def get_consent_registry_contract():
    return {
        "approval": ConsentRegistry.get_approval_program(),
        "clear": ConsentRegistry.get_clear_state_program(),
    }
