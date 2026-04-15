# DEPRECATED: PyTeal Contracts

This directory contains legacy PyTeal smart contracts that are **deprecated**.

## Status: DEPRECATED

These contracts are maintained for reference only. They should not be used for new deployments.

## Migration Path

Please use the **ARC4 contracts** in `contracts_v2/` directory instead.

### Why migrate?

| Feature            | PyTeal (`contracts/`) | ARC4 (`contracts_v2/`) |
| ------------------ | --------------------- | ---------------------- |
| Language           | PyTeal v0.27          | AlgoPy (ARC4)          |
| Type Safety        | Limited               | Full                   |
| ABI Support        | Manual                | Native                 |
| Testing            | Harder                | Easier                 |
| AlgoKit Compatible | Partial               | Full                   |
| Future Support     | Deprecated            | Active                 |

### How to migrate

1. Use contracts from `contracts_v2/` directory
2. Update your app IDs in environment variables
3. The ARC4 contracts provide the same functionality with better developer experience

### Contract Comparison

| PyTeal Contract       | ARC4 Equivalent                    |
| --------------------- | ---------------------------------- |
| `consent_registry.py` | `contracts_v2/consent_registry.py` |
| `audit_trail.py`      | `contracts_v2/audit_trail.py`      |

## Removal Timeline

- **Q2 2024**: Marked as deprecated
- **Q3 2024**: No longer receive updates
- **Q4 2024**: Scheduled for removal

## Questions?

Open an issue at: https://github.com/consentchain/consentchain/issues
