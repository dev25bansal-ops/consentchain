#!/usr/bin/env python3
import os
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from algosdk import account, mnemonic
from algosdk.v2client import algod
from algosdk import transaction

from contracts.consent_registry import get_consent_registry_contract
from contracts.audit_trail import get_audit_trail_contract
from contracts.client import AlgorandClient, ContractDeployer


def load_environment():
    from dotenv import load_dotenv

    load_dotenv()

    node_url = os.getenv("ALGORAND_NODE_URL", "https://testnet-api.algonode.cloud")
    indexer_url = os.getenv("ALGORAND_INDEXER_URL", "https://testnet-idx.algonode.cloud")
    master_mnemonic = os.getenv("MASTER_MNEMONIC")

    if not master_mnemonic:
        print("ERROR: MASTER_MNEMONIC not set in environment")
        sys.exit(1)

    return node_url, indexer_url, master_mnemonic


def deploy_consent_registry(algod_client, deployer_address, deployer_key):
    print("\n" + "=" * 60)
    print("Deploying Consent Registry Smart Contract...")
    print("=" * 60)

    consent_contracts = get_consent_registry_contract()
    approval_program = consent_contracts["approval"]
    clear_program = consent_contracts["clear"]

    approval_compiled = algod_client.compile(approval_program)
    clear_compiled = algod_client.compile(clear_program)

    approval_bytes = bytes.fromhex(approval_compiled["result"])
    clear_bytes = bytes.fromhex(clear_compiled["result"])

    params = algod_client.suggested_params()

    global_schema = transaction.StateSchema(
        num_uints=4,
        num_byte_slices=1,
    )

    local_schema = transaction.StateSchema(
        num_uints=3,
        num_byte_slices=7,
    )

    txn = transaction.ApplicationCreateTxn(
        deployer_address,
        params,
        transaction.OnComplete.NoOpOC,
        approval_bytes,
        clear_bytes,
        global_schema,
        local_schema,
        note=b"ConsentChain Consent Registry v1.0",
    )

    signed_txn = txn.sign(deployer_key)
    tx_id = algod_client.send_transaction(signed_txn)

    print(f"Transaction sent: {tx_id}")
    print("Waiting for confirmation...")

    result = transaction.wait_for_confirmation(algod_client, tx_id, 10)
    app_id = result["application-index"]

    print(f"Consent Registry deployed successfully!")
    print(f"Application ID: {app_id}")

    return app_id, tx_id


def deploy_audit_trail(algod_client, deployer_address, deployer_key):
    print("\n" + "=" * 60)
    print("Deploying Audit Trail Smart Contract...")
    print("=" * 60)

    audit_contracts = get_audit_trail_contract()
    approval_program = audit_contracts["approval"]
    clear_program = audit_contracts["clear"]

    approval_compiled = algod_client.compile(approval_program)
    clear_compiled = algod_client.compile(clear_program)

    approval_bytes = bytes.fromhex(approval_compiled["result"])
    clear_bytes = bytes.fromhex(clear_compiled["result"])

    params = algod_client.suggested_params()

    global_schema = transaction.StateSchema(
        num_uints=2,
        num_byte_slices=4,
    )

    local_schema = transaction.StateSchema(
        num_uints=0,
        num_byte_slices=0,
    )

    txn = transaction.ApplicationCreateTxn(
        deployer_address,
        params,
        transaction.OnComplete.NoOpOC,
        approval_bytes,
        clear_bytes,
        global_schema,
        local_schema,
        note=b"ConsentChain Audit Trail v1.0",
    )

    signed_txn = txn.sign(deployer_key)
    tx_id = algod_client.send_transaction(signed_txn)

    print(f"Transaction sent: {tx_id}")
    print("Waiting for confirmation...")

    result = transaction.wait_for_confirmation(algod_client, tx_id, 10)
    app_id = result["application-index"]

    print(f"Audit Trail deployed successfully!")
    print(f"Application ID: {app_id}")

    return app_id, tx_id


def fund_deployer_if_needed(algod_client, deployer_address, min_balance=1000000):
    balance_info = algod_client.account_info(deployer_address)
    balance = balance_info.get("amount", 0)

    if balance < min_balance:
        print(f"Deployer account has insufficient balance: {balance} microAlgos")
        print(f"Please fund the account: {deployer_address}")
        print(
            "You can use the Algorand Testnet Dispenser: https://testnet.algoexplorer.io/dispenser"
        )
        return False

    print(f"Deployer balance: {balance / 1_000_000:.2f} Algos")
    return True


def update_env_file(consent_app_id, audit_app_id):
    env_file = Path(__file__).parent.parent / ".env"

    if env_file.exists():
        with open(env_file, "r") as f:
            lines = f.readlines()

        updated_lines = []
        for line in lines:
            if line.startswith("CONSENT_REGISTRY_APP_ID="):
                updated_lines.append(f"CONSENT_REGISTRY_APP_ID={consent_app_id}\n")
            elif line.startswith("AUDIT_APP_ID="):
                updated_lines.append(f"AUDIT_APP_ID={audit_app_id}\n")
            else:
                updated_lines.append(line)

        if not any(l.startswith("CONSENT_REGISTRY_APP_ID=") for l in lines):
            updated_lines.append(f"\nCONSENT_REGISTRY_APP_ID={consent_app_id}\n")
        if not any(l.startswith("AUDIT_APP_ID=") for l in lines):
            updated_lines.append(f"AUDIT_APP_ID={audit_app_id}\n")

        with open(env_file, "w") as f:
            f.writelines(updated_lines)
    else:
        print(f"Warning: .env file not found at {env_file}")

    print(f"\nUpdated .env file with application IDs")


def save_deployment_info(consent_app_id, audit_app_id, deployer_address):
    deployment_info = {
        "network": os.getenv("ALGORAND_NETWORK", "testnet"),
        "deployer_address": deployer_address,
        "consent_registry_app_id": consent_app_id,
        "audit_trail_app_id": audit_app_id,
        "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }

    deployment_file = Path(__file__).parent.parent / "deployment.json"
    with open(deployment_file, "w") as f:
        json.dump(deployment_info, f, indent=2)

    print(f"Deployment info saved to {deployment_file}")


def main():
    print("=" * 60)
    print("ConsentChain Smart Contract Deployment")
    print("AlgoBharat Hack Series 3.0")
    print("=" * 60)

    node_url, indexer_url, master_mnemonic = load_environment()

    deployer_key = mnemonic.to_private_key(master_mnemonic)
    deployer_address = account.address_from_private_key(deployer_key)

    print(f"\nDeployer Address: {deployer_address}")

    algod_client = algod.AlgodClient("", node_url, headers={"User-Agent": "ConsentChain"})

    status = algod_client.status()
    print(f"Connected to node at round: {status['round']}")

    if not fund_deployer_if_needed(algod_client, deployer_address):
        sys.exit(1)

    consent_app_id, consent_tx_id = deploy_consent_registry(
        algod_client, deployer_address, deployer_key
    )

    audit_app_id, audit_tx_id = deploy_audit_trail(algod_client, deployer_address, deployer_key)

    update_env_file(consent_app_id, audit_app_id)
    save_deployment_info(consent_app_id, audit_app_id, deployer_address)

    print("\n" + "=" * 60)
    print("DEPLOYMENT COMPLETE")
    print("=" * 60)
    print(f"Consent Registry App ID: {consent_app_id}")
    print(f"Audit Trail App ID: {audit_app_id}")
    print(f"\nView on AlgoExplorer:")
    print(f"  https://testnet.algoexplorer.io/application/{consent_app_id}")
    print(f"  https://testnet.algoexplorer.io/application/{audit_app_id}")


if __name__ == "__main__":
    main()
