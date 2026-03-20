# DPDP Act Compliance Guide

## Overview

This document details how ConsentChain ensures compliance with India's **Digital Personal Data Protection Act 2023** (DPDP Act).

## Key DPDP Act Provisions Addressed

### 1. Consent Requirements (Section 6)

| DPDP Requirement                              | ConsentChain Implementation                                                                 |
| --------------------------------------------- | ------------------------------------------------------------------------------------------- |
| **Clear and specific consent request**        | API returns structured consent object with purpose, data types, and duration clearly stated |
| **Free, specific, informed, and unambiguous** | Dashboard displays all consent details before user action                                   |
| **Withdrawable consent**                      | One-click revocation via dashboard, instant on-chain recording                              |
| **Purpose limitation**                        | Each consent tied to specific purpose enum (MARKETING, ANALYTICS, etc.)                     |
| **Data minimization**                         | Only necessary data types listed per consent                                                |

### 2. Rights of Data Principal (Section 7)

| Right                            | ConsentChain Feature                                  |
| -------------------------------- | ----------------------------------------------------- |
| **Right to access**              | Dashboard shows all consents with full details        |
| **Right to correction**          | Consent modification flow with on-chain update        |
| **Right to erasure**             | Revocation triggers deletion workflow for fiduciaries |
| **Right to withdraw consent**    | Instant revocation, on-chain proof                    |
| **Right to grievance redressal** | Complete audit trail for disputes                     |
| **Right to nominate**            | (Future roadmap) Nominee management                   |

### 3. Sensitive Personal Data (Section 9)

ConsentChain recognizes all sensitive data categories:

```python
SENSITIVE_DATA_CATEGORIES = [
    "FINANCIAL_DATA",        # Bank accounts, transactions
    "HEALTH_DATA",           # Medical records, diagnoses
    "BIOMETRIC_DATA",        # Fingerprints, iris scans
    "SEXUAL_ORIENTATION",    # LGBTQ+ status
    "CASTE_OR_TRIBE",        # Social category
    "RELIGIOUS_BELIEFS",     # Religious affiliation
    "POLITICAL_OPINIONS",    # Political views
    "GENETIC_DATA",          # DNA, genetic markers
]
```

**Special handling for sensitive data:**

- Stricter consent validation
- Shorter default duration (90 days vs 365)
- Explicit opt-in required
- Third-party sharing requires additional consent

### 4. Cross-Border Data Transfer (Section 16)

ConsentChain tracks data movement:

```python
class DataTransferType(Enum):
    DOMESTIC = "DOMESTIC"           # Within India
    CROSS_BORDER = "CROSS_BORDER"   # Outside India
    THIRD_PARTY = "THIRD_PARTY"     # Shared with third party
```

Each consent explicitly states:

- Whether data leaves India
- Destination country (if applicable)
- Third-party recipients

### 5. Data Fiduciary Obligations (Section 8)

| Obligation                          | Implementation                                 |
| ----------------------------------- | ---------------------------------------------- |
| **Maintain accurate records**       | PostgreSQL database with immutable audit trail |
| **Implement security safeguards**   | Encryption, access controls, rate limiting     |
| **Notify data breach**              | Webhook integration for breach alerts          |
| **Appoint Data Protection Officer** | API endpoint for DPO registration              |
| **Data retention limits**           | Auto-expiry enforcement                        |

### 6. Consent Validity Periods

Default maximum durations by purpose:

| Purpose             | Max Duration | Rationale                       |
| ------------------- | ------------ | ------------------------------- |
| MARKETING           | 90 days      | Short-lived promotional consent |
| ANALYTICS           | 180 days     | Medium-term analytics           |
| SERVICE_DELIVERY    | 365 days     | Annual service renewal          |
| THIRD_PARTY_SHARING | 90 days      | Requires explicit renewal       |
| RESEARCH            | 365 days     | Research project duration       |
| PAYMENT_PROCESSING  | 365 days     | Transaction necessity           |
| COMPLIANCE          | 365 days     | Regulatory requirement          |

## Compliance Workflow

### Consent Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONSENT LIFECYCLE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐                                                          │
│   │   REQUEST    │  Data Principal receives consent request                 │
│   │   SENT       │  - Clear purpose statement                               │
│   └──────┬───────┘  - Data categories listed                                │
│          │          - Duration specified                                    │
│          ▼                                                                  │
│   ┌──────────────┐                                                          │
│   │   REVIEW     │  Principal reviews details                               │
│   │   PHASE      │  - Can modify selections                                 │
│   └──────┬───────┘  - Can reject entirely                                   │
│          │                                                                  │
│          ▼                                                                  │
│   ┌──────────────┐                                                          │
│   │   GRANT      │  Principal signs and approves                            │
│   │   CONSENT    │  - Ed25519 signature                                     │
│   └──────┬───────┘  - On-chain recording                                    │
│          │          - Hash generated                                        │
│          ▼                                                                  │
│   ┌──────────────┐                                                          │
│   │   ACTIVE     │  Consent is active                                       │
│   │   STATE      │  - Data can be processed                                 │
│   └──────┬───────┘  - Regular verification                                  │
│          │          - Expiry monitoring                                     │
│          │                                                                  │
│          ├───────────────────────┐                                          │
│          │                       │                                          │
│          ▼                       ▼                                          │
│   ┌──────────────┐       ┌──────────────┐                                   │
│   │    MODIFY    │       │    REVOKE    │                                   │
│   │   (Optional) │       │    (Anytime) │                                   │
│   └──────┬───────┘       └──────┬───────┘                                   │
│          │                      │                                           │
│          │                      ▼                                           │
│          │              ┌──────────────┐                                    │
│          │              │   REVOKED    │                                    │
│          │              │    STATE     │                                    │
│          │              └──────────────┘                                    │
│          │              - Data deletion                                     │
│          │                initiated                                         │
│          │              - Third parties                                     │
│          │                notified                                          │
│          │                                                                  │
│          ▼                                                                  │
│   ┌──────────────┐                                                          │
│   │   EXPIRE     │  Consent reaches end date                                │
│   │   (Auto)     │  - Status updated                                        │
│   └──────────────┘  - Data processing stops                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Compliance Checklist for Data Fiduciaries

### Pre-Deployment Checklist

- [ ] Register as Data Fiduciary in ConsentChain
- [ ] Configure API credentials
- [ ] Define data categories collected
- [ ] Specify purposes for data use
- [ ] Set up data retention policies
- [ ] Configure breach notification webhooks
- [ ] Integrate SDK into existing systems
- [ ] Train staff on consent management

### Ongoing Compliance

- [ ] Request consent before data collection
- [ ] Verify consent status before processing
- [ ] Log all data access events
- [ ] Monitor consent expiry dates
- [ ] Process revocation within 30 days
- [ ] Generate monthly compliance reports
- [ ] Conduct quarterly audits

## Penalties and Risk Mitigation

### DPDP Act Penalties (Section 33)

| Violation                             | Maximum Penalty | ConsentChain Mitigation              |
| ------------------------------------- | --------------- | ------------------------------------ |
| Data breach notification failure      | ₹200 crore      | Automated breach alerts via webhooks |
| Non-compliance with children's data   | ₹200 crore      | Age verification integration points  |
| Failure to respond to Data Principal  | ₹50 crore       | Automated response tracking          |
| Breach of cross-border transfer rules | ₹250 crore      | Geographic tracking in consent       |

### ConsentChain Risk Mitigation

1. **Immutable Proof**: On-chain records cannot be altered
2. **Complete Audit Trail**: Every action logged with timestamps
3. **Instant Revocation Processing**: Automated workflows
4. **Regular Compliance Reports**: Automated generation
5. **Third-Party Verification**: Regulators can query directly

## Integration Points for Regulators

### Audit Access API

```http
GET /api/v1/regulator/audit/{fiduciary_id}
Authorization: Bearer <regulator_token>

Response:
{
  "fiduciary_id": "uuid",
  "total_consents": 10000,
  "active_consents": 8500,
  "revoked_consents": 1000,
  "expired_consents": 500,
  "compliance_score": 95,
  "last_audit": "2024-01-01T00:00:00Z",
  "on_chain_verification": "https://algoexplorer.io/tx/..."
}
```

### Merkle Proof Verification

```http
POST /api/v1/regulator/verify-proof
Authorization: Bearer <regulator_token>

{
  "event_id": "uuid",
  "merkle_proof": ["hash1", "hash2", ...],
  "merkle_root": "0x..."
}

Response:
{
  "verified": true,
  "on_chain_root": "0x...",
  "block_height": 12345678,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Future DPDP Compliance Features

### Roadmap for Additional Compliance

| Feature                                   | DPDP Section | Status  |
| ----------------------------------------- | ------------ | ------- |
| Children's Data Protection                | Section 9    | Planned |
| Data Protection Officer Portal            | Section 8    | Planned |
| Cross-Border Transfer Restrictions        | Section 16   | Planned |
| Significant Data Fiduciary Classification | Section 10   | Planned |
| Consent Manager Integration               | Section 6    | Planned |

## Legal Disclaimer

ConsentChain provides technical infrastructure for consent management. Organizations using ConsentChain should:

1. Consult with legal counsel for specific compliance requirements
2. Review internal data processing practices
3. Ensure all third-party integrations are compliant
4. Maintain additional documentation as required by law
5. Conduct regular compliance assessments

This solution assists with DPDP compliance but does not guarantee legal compliance. Organizations remain responsible for their own regulatory adherence.

---

_For legal advice regarding DPDP Act compliance, please consult a qualified data protection attorney in India._
