# Technical Architecture Deep Dive

## Overview

ConsentChain implements a two-layer architecture to balance transparency with privacy, leveraging Algorand's high-throughput, low-cost blockchain infrastructure.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │ Data Principal   │  │ Data Fiduciary   │  │   Regulator      │          │
│  │    Dashboard     │  │   Enterprise App │  │   Audit Portal   │          │
│  │   (Vue.js SPA)   │  │   (SDK Client)   │  │   (API Access)   │          │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘          │
│           │                     │                     │                     │
└───────────┼─────────────────────┼─────────────────────┼─────────────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    FastAPI Application Server                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │   Auth      │  │   Consent   │  │    Audit    │  │ Compliance  │  │  │
│  │  │  Middleware │  │   Service   │  │   Service   │  │   Service   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
└──────────────────────────────┼──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OFF-CHAIN DATA LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐   │
│  │    PostgreSQL      │  │      Redis         │  │   IPFS (Optional)  │   │
│  │  ┌──────────────┐  │  │  ┌──────────────┐  │  │  ┌──────────────┐  │   │
│  │  │   Principals │  │  │  │   Session    │  │  │  │   Consent    │  │   │
│  │  │   Fiduciaries│  │  │  │   Cache      │  │  │  │   Metadata   │  │   │
│  │  │   Consents   │  │  │  │   Queue      │  │  │  │   Documents  │  │   │
│  │  │   Events     │  │  │  └──────────────┘  │  │  └──────────────┘  │   │
│  │  │   Audit Logs │  │  │                    │  │                    │   │
│  │  └──────────────┘  │  │                    │  │                    │   │
│  └────────────────────┘  └────────────────────┘  └────────────────────┘   │
│                              │                                              │
└──────────────────────────────┼──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ON-CHAIN LAYER (ALGORAND)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────┐  ┌────────────────────────────────┐    │
│  │    Consent Registry App        │  │      Audit Trail App           │    │
│  │  ┌──────────────────────────┐  │  │  ┌──────────────────────────┐  │    │
│  │  │  Local State (per user)  │  │  │  │  Global State            │  │    │
│  │  │  - principal_address     │  │  │  │  - event_counter         │  │    │
│  │  │  - fiduciary_address     │  │  │  │  - merkle_root           │  │    │
│  │  │  - purpose               │  │  │  │  - last_event_hash       │  │    │
│  │  │  - data_types_hash       │  │  │  └──────────────────────────┘  │    │
│  │  │  - status                │  │  │                                │    │
│  │  │  - consent_hash          │  │  │  Operations:                   │    │
│  │  └──────────────────────────┘  │  │  - log_event                   │    │
│  │                                │  │  - batch_log                    │    │
│  │  Operations:                   │  │  - get_root                     │    │
│  │  - register                   │  │  - verify_proof                 │    │
│  │  - revoke                     │  │                                │    │
│  │  - modify                     │  │                                │    │
│  │  - verify                     │  │                                │    │
│  └────────────────────────────────┘  └────────────────────────────────┘    │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      Algorand Blockchain                              │  │
│  │  - Pure Proof of Stake consensus                                      │  │
│  │  - ~1000 TPS throughput                                               │  │
│  │  - ~4 second block time                                               │  │
│  │  - $0.001 transaction cost                                            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagrams

### Consent Creation Flow

```
Data Principal          API Server              Database               Algorand
     │                      │                      │                      │
     │ 1. Connect Wallet    │                      │                      │
     │─────────────────────>│                      │                      │
     │                      │                      │                      │
     │ 2. Consent Request   │                      │                      │
     │    (purpose, data)   │                      │                      │
     │─────────────────────>│                      │                      │
     │                      │                      │                      │
     │                      │ 3. Validate Request  │                      │
     │                      │    (DPDP checks)     │                      │
     │                      │                      │                      │
     │                      │ 4. Generate Hash     │                      │
     │                      │    consent_hash      │                      │
     │                      │                      │                      │
     │                      │ 5. Store Consent     │                      │
     │                      │─────────────────────>│                      │
     │                      │                      │                      │
     │                      │ 6. Call Contract     │                      │
     │                      │─────────────────────────────────────────────>│
     │                      │                      │                      │
     │                      │                      │    7. Store on-chain │
     │                      │                      │<─────────────────────│
     │                      │                      │                      │
     │                      │ 8. Return TX ID      │                      │
     │                      │<─────────────────────────────────────────────│
     │                      │                      │                      │
     │                      │ 9. Update Record     │                      │
     │                      │─────────────────────>│                      │
     │                      │                      │                      │
     │ 10. Consent Created  │                      │                      │
     │<─────────────────────│                      │                      │
     │                      │                      │                      │
```

### Consent Verification Flow

```
Data Fiduciary          API Server              Database               Algorand
     │                      │                      │                      │
     │ 1. Verify Request    │                      │                      │
     │    (consent_id)      │                      │                      │
     │─────────────────────>│                      │                      │
     │                      │                      │                      │
     │                      │ 2. Query Database    │                      │
     │                      │─────────────────────>│                      │
     │                      │                      │                      │
     │                      │ 3. Return Record     │                      │
     │                      │<─────────────────────│                      │
     │                      │                      │                      │
     │                      │ 4. Check Status      │                      │
     │                      │    - Status field    │                      │
     │                      │    - Expiry date     │                      │
     │                      │                      │                      │
     │                      │ 5. Verify On-Chain   │                      │
     │                      │─────────────────────────────────────────────>│
     │                      │                      │                      │
     │                      │ 6. Confirm Hash      │                      │
     │                      │<─────────────────────────────────────────────│
     │                      │                      │                      │
     │ 7. Verification      │                      │                      │
     │    Result            │                      │                      │
     │<─────────────────────│                      │                      │
     │                      │                      │                      │
```

## Smart Contract State Management

### Consent Registry State Schema

```python
# Global State
global_state = {
    "total_consents": Uint64,      # Total number of consents recorded
    "active_consents": Uint64,     # Currently active consents
    "revoked_consents": Uint64,    # Total revoked consents
    "admin_address": Bytes,        # Contract administrator
}

# Local State (per user account)
local_state = {
    "principal_address": Bytes,    # Data Principal's wallet
    "fiduciary_address": Bytes,    # Data Fiduciary's wallet
    "purpose": Bytes,              # Purpose enum (MARKETING, etc.)
    "data_types_hash": Bytes,      # SHA-256 of data categories JSON
    "status": Uint64,              # 0=Pending, 1=Granted, 2=Revoked, 3=Expired
    "granted_at": Uint64,          # Block round when granted
    "expires_at": Uint64,          # Block round when expires (optional)
    "consent_hash": Bytes,         # Unique consent identifier
}
```

### Audit Trail State Schema

```python
# Global State
global_state = {
    "event_counter": Uint64,       # Total events logged
    "merkle_root": Bytes,          # Current Merkle tree root
    "last_event_hash": Bytes,      # Hash of last event
    "admin_address": Bytes,        # Authorized auditor
}
```

## Cryptographic Schemes

### Consent Hash Generation

```
consent_hash = SHA256(
    canonical_json({
        "principal_id": "uuid",
        "fiduciary_id": "uuid",
        "purpose": "MARKETING",
        "data_types": ["PERSONAL_INFO", "CONTACT_INFO"],
        "timestamp": "2024-01-01T00:00:00Z",
        "nonce": "random_16_bytes_hex"
    })
)
```

### Merkle Tree Construction

```
Event Hash = SHA256(event_id + event_type + timestamp + previous_hash)

Level 0 (Leaves):  [H0] [H1] [H2] [H3] [H4] [H5] [H6] [H7]
                     │    │    │    │    │    │    │    │
Level 1:           [H01]  [H23]  [H45]  [H67]
                     │      │      │      │
Level 2:           [H0123]  [H4567]
                     │        │
Level 3 (Root):    [H01234567]  ← Merkle Root stored on-chain
```

### Ed25519 Signature Flow

```
1. Principal signs consent request:
   signature = Sign(private_key, consent_hash)

2. Contract verifies signature:
   valid = Verify(public_key, consent_hash, signature)

3. Signature stored with event for audit trail
```

## API Security Model

### Authentication Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Data Fiduciary Auth                          │
├─────────────────────────────────────────────────────────────────┤
│  1. Register → receive API key                                   │
│  2. API key stored as SHA-256 hash                               │
│  3. Each request: Authorization: Bearer <api_key>               │
│  4. Server validates: hash(api_key) == stored_hash              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Data Principal Auth                          │
├─────────────────────────────────────────────────────────────────┤
│  1. Connect wallet (Algorand wallet integration)                │
│  2. Sign challenge message                                       │
│  3. Server verifies signature, issues JWT                        │
│  4. Subsequent requests: Authorization: Bearer <jwt>            │
│  5. JWT contains: principal_id, wallet_address, exp, iat        │
└─────────────────────────────────────────────────────────────────┘
```

## Database Schema (PostgreSQL)

### Entity Relationship Diagram

```
┌───────────────────┐       ┌───────────────────┐
│   data_principals │       │  data_fiduciaries │
├───────────────────┤       ├───────────────────┤
│ id (PK)           │       │ id (PK)           │
│ wallet_address    │       │ name              │
│ email_hash        │       │ registration_num  │
│ phone_hash        │       │ wallet_address    │
│ kyc_verified      │       │ api_key_hash      │
│ created_at        │       │ data_categories   │
└────────┬──────────┘       │ purposes          │
         │                  │ compliance_status │
         │                  └────────┬──────────┘
         │                           │
         │                           │
         │    ┌──────────────────────┴──────────────────────┐
         │    │                                               │
         ▼    ▼                                               │
┌───────────────────────────────┐                            │
│       consent_records         │                            │
├───────────────────────────────┤                            │
│ id (PK)                       │                            │
│ principal_id (FK)─────────────┼────────────────────────────┘
│ fiduciary_id (FK)─────────────┼────────────────────────────┘
│ purpose                       │
│ data_types (JSON)             │
│ status                        │
│ granted_at                    │
│ expires_at                    │
│ revoked_at                    │
│ on_chain_tx_id                │
│ consent_hash                  │
│ created_at                    │
└───────────────┬───────────────┘
                │
                │ 1:N
                ▼
┌───────────────────────────────┐
│       consent_events          │
├───────────────────────────────┤
│ id (PK)                       │
│ consent_id (FK)               │
│ event_type                    │
│ actor                         │
│ actor_type                    │
│ previous_status               │
│ new_status                    │
│ tx_id                         │
│ block_number                  │
│ signature                     │
│ created_at                    │
└───────────────────────────────┘

┌───────────────────────────────┐       ┌───────────────────────────────┐
│         audit_logs            │       │      compliance_reports       │
├───────────────────────────────┤       ├───────────────────────────────┤
│ id (PK)                       │       │ id (PK)                       │
│ principal_id (FK)             │       │ fiduciary_id (FK)             │
│ fiduciary_id (FK)             │       │ period_start                  │
│ action                        │       │ period_end                    │
│ resource_type                 │       │ total_consents                │
│ resource_id                   │       │ active_consents               │
│ on_chain_reference            │       │ compliance_score              │
│ created_at                    │       │ on_chain_hash                 │
└───────────────────────────────┘       └───────────────────────────────┘

┌───────────────────────────────┐
│       merkle_roots            │
├───────────────────────────────┤
│ id (PK)                       │
│ root_hash (UNIQUE)            │
│ event_count                   │
│ first_event_id                │
│ last_event_id                 │
│ on_chain_tx_id                │
│ created_at                    │
└───────────────────────────────┘
```

## Performance Considerations

### Algorand Transaction Costs

| Operation        | Cost (ALGO) | Cost (INR approx.) |
| ---------------- | ----------- | ------------------ |
| Create consent   | ~0.001      | ~₹0.08             |
| Revoke consent   | ~0.001      | ~₹0.08             |
| Batch log events | ~0.001      | ~₹0.08             |
| Query (no TX)    | 0           | ₹0                 |

### Throughput Metrics

| Metric               | Value                       |
| -------------------- | --------------------------- |
| API requests/sec     | 1000+                       |
| On-chain TX/sec      | Limited by Algorand (~1000) |
| Database queries/sec | 10,000+                     |
| Cache hit rate       | >95%                        |

### Scalability Patterns

1. **Horizontal API Scaling**: Multiple FastAPI instances behind load balancer
2. **Database Read Replicas**: PostgreSQL read replicas for query distribution
3. **Redis Caching**: Consent status cached for 60 seconds
4. **Batch Operations**: Multiple consents in single API call
5. **Event Aggregation**: Merkle roots computed in batches

## Disaster Recovery

### Backup Strategy

1. **Database**: Daily PostgreSQL backups, point-in-time recovery
2. **Blockchain**: Algorand is inherently replicated
3. **API State**: Stateless design, no local state
4. **Configuration**: Version controlled (except secrets)

### High Availability

```
┌─────────────────────────────────────────────────────────────────┐
│                         Load Balancer                           │
└─────────────────────────────┬───────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │  API 1   │   │  API 2   │   │  API 3   │
        └────┬─────┘   └────┬─────┘   └────┬─────┘
             │              │              │
             └──────────────┼──────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │   PGB    │ │  PG Rep  │ │  Redis   │
        │  Primary │ │  Read-1  │ │  Cluster │
        └──────────┘ └──────────┘ └──────────┘
```

## Security Hardening

### Input Validation

- Wallet addresses: 58-character base32 validation
- UUIDs: RFC 4122 format validation
- Enum fields: Whitelist validation
- JSON fields: Schema validation, max depth

### Rate Limiting

```python
# Enterprise tier
RATE_LIMITS = {
    "consent_create": "100/minute",
    "consent_verify": "1000/minute",
    "consent_query": "500/minute",
    "audit_query": "100/minute",
}
```

### Audit Trail Integrity

All operations logged with:

- Timestamp (ISO 8601)
- Actor identification
- Previous and new state
- Cryptographic signature
- On-chain reference (when applicable)

---

_This architecture ensures compliance with India's DPDP Act while providing enterprise-grade performance and security._
