from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod, indexer
from typing import Optional, Dict, Any, List, Tuple
import json
import base64
import os
from dotenv import load_dotenv

load_dotenv()


class AlgorandClient:
    def __init__(
        self,
        node_url: Optional[str] = None,
        indexer_url: Optional[str] = None,
        network: str = "testnet",
    ):
        self.node_url = node_url or os.getenv(
            "ALGORAND_NODE_URL", "https://testnet-api.algonode.cloud"
        )
        self.indexer_url = indexer_url or os.getenv(
            "ALGORAND_INDEXER_URL", "https://testnet-idx.algonode.cloud"
        )
        self.network = network

        self.algod_client = algod.AlgodClient(
            algod_token="", algod_address=self.node_url, headers={"User-Agent": "ConsentChain/1.0"}
        )

        self.indexer_client = indexer.IndexerClient(
            indexer_token="",
            indexer_address=self.indexer_url,
            headers={"User-Agent": "ConsentChain/1.0"},
        )

        self._master_account: Optional[Dict] = None

    def get_account_info(self, address: str) -> Dict[str, Any]:
        return self.algod_client.account_info(address)

    def get_application_info(self, app_id: int) -> Dict[str, Any]:
        return self.algod_client.application_info(app_id)

    def get_asset_info(self, asset_id: int) -> Dict[str, Any]:
        return self.algod_client.asset_info(asset_id)

    def get_transaction_params(self) -> transaction.SuggestedParams:
        return self.algod_client.suggested_params()

    def get_status(self) -> Dict[str, Any]:
        return self.algod_client.status()

    def get_block_info(self, round_number: int) -> Dict[str, Any]:
        return self.algod_client.block_info(round_number)

    def load_master_account(self, mnemonics: Optional[str] = None) -> Dict[str, str]:
        mnemonics = mnemonics or os.getenv("MASTER_MNEMONIC")
        if not mnemonics:
            raise ValueError("Master mnemonic not provided")

        private_key = mnemonic.to_private_key(mnemonics)
        address = account.address_from_private_key(private_key)

        self._master_account = {
            "address": address,
            "private_key": private_key,
        }
        return self._master_account

    @property
    def master_account(self) -> Dict[str, str]:
        if self._master_account is None:
            self.load_master_account()
        return self._master_account

    def generate_new_account(self) -> Dict[str, str]:
        private_key, address = account.generate_account()
        mnemonics = mnemonic.from_private_key(private_key)
        return {
            "address": address,
            "private_key": private_key,
            "mnemonic": mnemonics,
        }

    def check_balance(self, address: str) -> int:
        account_info = self.get_account_info(address)
        return account_info.get("amount", 0)

    def fund_account(
        self,
        receiver: str,
        amount_micro_algos: int,
        sender: Optional[str] = None,
        sender_key: Optional[str] = None,
    ) -> str:
        if sender is None or sender_key is None:
            sender = self.master_account["address"]
            sender_key = self.master_account["private_key"]

        params = self.get_transaction_params()
        txn = transaction.PaymentTxn(sender, params, receiver, amount_micro_algos)
        signed_txn = txn.sign(sender_key)
        tx_id = self.algod_client.send_transaction(signed_txn)

        transaction.wait_for_confirmation(self.algod_client, tx_id, 4)
        return tx_id

    def wait_for_transaction(self, tx_id: str, timeout: int = 10) -> Dict[str, Any]:
        return transaction.wait_for_confirmation(self.algod_client, tx_id, timeout)

    def search_transactions_by_address(
        self,
        address: str,
        limit: int = 100,
        min_round: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        response = self.indexer_client.search_transactions_by_address(
            address, limit=limit, min_round=min_round
        )
        return response.get("transactions", [])

    def search_transactions_by_app(
        self,
        app_id: int,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        response = self.indexer_client.search_transactions(
            note_prefix=None,
            txn_type="appl",
            limit=limit,
            app_id=app_id,
        )
        return response.get("transactions", [])

    def get_application_local_state(
        self,
        app_id: int,
        address: str,
    ) -> Optional[Dict[str, Any]]:
        account_info = self.get_account_info(address)

        for app_data in account_info.get("apps-local-state", []):
            if app_data.get("id") == app_id:
                return app_data

        return None

    def decode_application_state(self, state: Dict) -> Dict[str, Any]:
        decoded = {}

        for item in state.get("key-value", []):
            key = base64.b64decode(item["key"]).decode("utf-8")

            if item["value"]["type"] == 1:
                decoded[key] = base64.b64decode(item["value"]["bytes"])
            else:
                decoded[key] = item["value"]["uint"]

        return decoded


class ContractDeployer:
    def __init__(self, client: AlgorandClient):
        self.client = client

    def compile_program(self, teal_source: str) -> bytes:
        compile_response = self.client.algod_client.compile(teal_source)
        return base64.b64decode(compile_response["result"])

    def deploy_consent_registry(
        self,
        approval_program: str,
        clear_program: str,
        creator: Optional[str] = None,
        creator_key: Optional[str] = None,
    ) -> Tuple[int, str]:
        if creator is None or creator_key is None:
            creator = self.client.master_account["address"]
            creator_key = self.client.master_account["private_key"]

        approval_compiled = self.compile_program(approval_program)
        clear_compiled = self.compile_program(clear_program)

        params = self.client.get_transaction_params()

        global_schema = transaction.StateSchema(
            num_uints=4,
            num_byte_slices=1,
        )

        local_schema = transaction.StateSchema(
            num_uints=3,
            num_byte_slices=7,
        )

        txn = transaction.ApplicationCreateTxn(
            creator,
            params,
            transaction.OnComplete.NoOpOC,
            approval_compiled,
            clear_compiled,
            global_schema,
            local_schema,
        )

        signed_txn = txn.sign(creator_key)
        tx_id = self.client.algod_client.send_transaction(signed_txn)

        tx_info = self.client.wait_for_transaction(tx_id)
        app_id = tx_info["application-index"]

        return app_id, tx_id

    def deploy_audit_trail(
        self,
        approval_program: str,
        clear_program: str,
        registry_app_id: int,
        creator: Optional[str] = None,
        creator_key: Optional[str] = None,
    ) -> Tuple[int, str]:
        if creator is None or creator_key is None:
            creator = self.client.master_account["address"]
            creator_key = self.client.master_account["private_key"]

        approval_compiled = self.compile_program(approval_program)
        clear_compiled = self.compile_program(clear_program)

        params = self.client.get_transaction_params()

        global_schema = transaction.StateSchema(
            num_uints=2,
            num_byte_slices=4,
        )

        local_schema = transaction.StateSchema(
            num_uints=0,
            num_byte_slices=0,
        )

        txn = transaction.ApplicationCreateTxn(
            creator,
            params,
            transaction.OnComplete.NoOpOC,
            approval_compiled,
            clear_compiled,
            global_schema,
            local_schema,
            app_args=[registry_app_id.to_bytes(8, "big")],
        )

        signed_txn = txn.sign(creator_key)
        tx_id = self.client.algod_client.send_transaction(signed_txn)

        tx_info = self.client.wait_for_transaction(tx_id)
        app_id = tx_info["application-index"]

        return app_id, tx_id


class ConsentContractClient:
    def __init__(self, client: AlgorandClient, app_id: int):
        self.client = client
        self.app_id = app_id

    def register_consent(
        self,
        principal_address: str,
        fiduciary_address: str,
        purpose: str,
        data_types_hash: str,
        consent_hash: str,
        expires_at: Optional[int] = None,
        sender_key: Optional[str] = None,
    ) -> str:
        if sender_key is None:
            sender_key = self.client.master_account["private_key"]

        params = self.client.get_transaction_params()

        app_args = [
            b"register",
            principal_address.encode(),
            fiduciary_address.encode(),
            purpose.encode(),
            data_types_hash.encode(),
            consent_hash.encode(),
        ]

        if expires_at:
            app_args.append(expires_at.to_bytes(8, "big"))

        txn = transaction.ApplicationNoOpTxn(
            self.client.master_account["address"],
            params,
            self.app_id,
            app_args=app_args,
        )

        signed_txn = txn.sign(sender_key)
        tx_id = self.client.algod_client.send_transaction(signed_txn)
        self.client.wait_for_transaction(tx_id)

        return tx_id

    def revoke_consent(self, principal_key: str) -> str:
        params = self.client.get_transaction_params()

        principal_address = account.address_from_private_key(principal_key)

        txn = transaction.ApplicationNoOpTxn(
            principal_address,
            params,
            self.app_id,
            app_args=[b"revoke"],
        )

        signed_txn = txn.sign(principal_key)
        tx_id = self.client.algod_client.send_transaction(signed_txn)
        self.client.wait_for_transaction(tx_id)

        return tx_id

    def verify_consent(self, consent_id: str, verifier_key: str) -> bool:
        params = self.client.get_transaction_params()
        verifier_address = account.address_from_private_key(verifier_key)

        try:
            txn = transaction.ApplicationNoOpTxn(
                verifier_address,
                params,
                self.app_id,
                app_args=[b"verify", consent_id.encode()],
            )

            signed_txn = txn.sign(verifier_key)
            tx_id = self.client.algod_client.send_transaction(signed_txn)
            self.client.wait_for_transaction(tx_id)

            return True
        except Exception:
            return False

    def get_consent_status(self, principal_address: str) -> Dict[str, Any]:
        state = self.client.get_application_local_state(self.app_id, principal_address)

        if state is None:
            return {"status": "NOT_FOUND"}

        decoded_state = self.client.decode_application_state(state)
        return decoded_state


class AuditTrailClient:
    def __init__(self, client: AlgorandClient, app_id: int):
        self.client = client
        self.app_id = app_id

    def log_event(
        self,
        event_type: str,
        consent_id: str,
        event_data: str,
        merkle_root: Optional[str] = None,
    ) -> str:
        params = self.client.get_transaction_params()

        app_args = [
            b"log_event",
            event_type.encode(),
            consent_id.encode(),
            event_data.encode(),
        ]

        if merkle_root:
            app_args.append(merkle_root.encode())

        txn = transaction.ApplicationNoOpTxn(
            self.client.master_account["address"],
            params,
            self.app_id,
            app_args=app_args,
        )

        signed_txn = txn.sign(self.client.master_account["private_key"])
        tx_id = self.client.algod_client.send_transaction(signed_txn)
        self.client.wait_for_transaction(tx_id)

        return tx_id

    def batch_log_events(
        self,
        merkle_root: str,
        event_count: int,
        last_event_hash: str,
    ) -> str:
        params = self.client.get_transaction_params()

        app_args = [
            b"batch_log",
            merkle_root.encode(),
            event_count.to_bytes(8, "big"),
            last_event_hash.encode(),
        ]

        txn = transaction.ApplicationNoOpTxn(
            self.client.master_account["address"],
            params,
            self.app_id,
            app_args=app_args,
        )

        signed_txn = txn.sign(self.client.master_account["private_key"])
        tx_id = self.client.algod_client.send_transaction(signed_txn)
        self.client.wait_for_transaction(tx_id)

        return tx_id

    def get_merkle_root(self) -> str:
        app_info = self.client.get_application_info(self.app_id)

        for item in app_info.get("params", {}).get("global-state", []):
            key = base64.b64decode(item["key"]).decode("utf-8")
            if key == "merkle_root":
                return base64.b64decode(item["value"]["bytes"]).decode("utf-8")

        return ""
