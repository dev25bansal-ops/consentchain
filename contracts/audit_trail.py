from pyteal import *
from typing import Final


class AuditTrailContract:
    VERSION: Final[int] = 1

    class GlobalState:
        event_counter = Bytes("event_counter")
        merkle_root = Bytes("merkle_root")
        last_event_hash = Bytes("last_hash")
        admin_address = Bytes("admin")
        registry_app_id = Bytes("registry_app")

    class AppArgs:
        ACTION_LOG_EVENT = Bytes("log_event")
        ACTION_BATCH_LOG = Bytes("batch_log")
        ACTION_GET_ROOT = Bytes("get_root")
        ACTION_VERIFY_PROOF = Bytes("verify_proof")

    @staticmethod
    def approval_program():
        action = Txn.application_args[0]

        log_single_event = Seq(
            [
                Assert(Txn.application_args.length() >= Int(5)),
                Assert(Txn.sender() == App.globalGet(AuditTrailContract.GlobalState.admin_address)),
                event_hash := Sha512_256(
                    Concat(
                        Txn.application_args[1],
                        Txn.application_args[2],
                        Txn.application_args[3],
                        Itob(Global.round()),
                        App.globalGet(AuditTrailContract.GlobalState.last_event_hash),
                    )
                ),
                App.globalPut(AuditTrailContract.GlobalState.last_event_hash, event_hash),
                App.globalPut(
                    AuditTrailContract.GlobalState.event_counter,
                    App.globalGet(AuditTrailContract.GlobalState.event_counter) + Int(1),
                ),
                If(Txn.application_args.length() > Int(5)).Then(
                    App.globalPut(
                        AuditTrailContract.GlobalState.merkle_root, Txn.application_args[5]
                    )
                ),
                Approve(),
            ]
        )

        batch_log_events = Seq(
            [
                Assert(Txn.application_args.length() >= Int(4)),
                Assert(Txn.sender() == App.globalGet(AuditTrailContract.GlobalState.admin_address)),
                batch_merkle_root := Txn.application_args[1],
                batch_count := Btoi(Txn.application_args[2]),
                last_event_in_batch := Txn.application_args[3],
                App.globalPut(AuditTrailContract.GlobalState.merkle_root, batch_merkle_root),
                App.globalPut(AuditTrailContract.GlobalState.last_event_hash, last_event_in_batch),
                App.globalPut(
                    AuditTrailContract.GlobalState.event_counter,
                    App.globalGet(AuditTrailContract.GlobalState.event_counter) + batch_count,
                ),
                Approve(),
            ]
        )

        get_root = Seq([Approve()])

        verify_event_proof = Seq(
            [
                Assert(Txn.application_args.length() >= Int(4)),
                event_data := Txn.application_args[1],
                proof_hashes := Txn.application_args[2],
                expected_root := Txn.application_args[3],
                computed_root := event_data,
                Approve(),
            ]
        )

        program = Cond(
            [action == AuditTrailContract.AppArgs.ACTION_LOG_EVENT, log_single_event],
            [action == AuditTrailContract.AppArgs.ACTION_BATCH_LOG, batch_log_events],
            [action == AuditTrailContract.AppArgs.ACTION_GET_ROOT, get_root],
            [action == AuditTrailContract.AppArgs.ACTION_VERIFY_PROOF, verify_event_proof],
        )

        return program

    @staticmethod
    def clear_state_program():
        return Approve()

    @staticmethod
    def get_approval_program():
        return compileTeal(AuditTrailContract.approval_program(), Mode.Application, version=8)

    @staticmethod
    def get_clear_state_program():
        return compileTeal(AuditTrailContract.clear_state_program(), Mode.Application, version=8)


class ComplianceToken:
    FIDUCIARY_COMPLIANCE_ASA_NAME = "ConsentChain Compliance Token"

    @staticmethod
    def create_compliance_token():
        return Seq(
            [
                Assert(Txn.sender() == Global.creator_address()),
                InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.AssetConfig,
                        TxnField.config_asset_name: Bytes(
                            ComplianceToken.FIDUCIARY_COMPLIANCE_ASA_NAME
                        ),
                        TxnField.config_asset_unit_name: Bytes("CC-COMPLY"),
                        TxnField.config_asset_total: Int(1000000),
                        TxnField.config_asset_decimals: Int(0),
                        TxnField.config_asset_default_frozen: Int(0),
                        TxnField.config_asset_manager: Global.creator_address(),
                        TxnField.config_asset_reserve: Global.creator_address(),
                        TxnField.note: Bytes("ConsentChain Compliance Token for Data Fiduciaries"),
                    }
                ),
                InnerTxnBuilder.Submit(),
                Approve(),
            ]
        )

    @staticmethod
    def mint_compliance_token():
        return Seq(
            [
                Assert(Txn.application_args.length() >= Int(3)),
                Assert(Txn.sender() == Global.creator_address()),
                fiduciary_address := Txn.application_args[1],
                compliance_score := Btoi(Txn.application_args[2]),
                InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.AssetTransfer,
                        TxnField.xfer_asset: Txn.assets[0],
                        TxnField.asset_receiver: fiduciary_address,
                        TxnField.asset_amount: compliance_score,
                    }
                ),
                InnerTxnBuilder.Submit(),
                Approve(),
            ]
        )

    @staticmethod
    def revoke_compliance_token():
        return Seq(
            [
                Assert(Txn.sender() == Global.creator_address()),
                InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.AssetTransfer,
                        TxnField.xfer_asset: Txn.assets[0],
                        TxnField.asset_sender: Txn.application_args[1],
                        TxnField.asset_receiver: Global.creator_address(),
                        TxnField.asset_amount: AssetHolding.balance(
                            Txn.application_args[1], Txn.assets[0]
                        ),
                    }
                ),
                InnerTxnBuilder.Submit(),
                Approve(),
            ]
        )


def get_audit_trail_contract():
    return {
        "approval": AuditTrailContract.get_approval_program(),
        "clear": AuditTrailContract.get_clear_state_program(),
    }
