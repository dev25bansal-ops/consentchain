# GDPR Compliance Guide

## Overview

This document details how **ConsentChain** ensures compliance with the **European Union's General Data Protection Regulation (GDPR)** — Regulation (EU) 2016/679. ConsentChain was originally designed for India's DPDP Act 2023 and has been extended to support the stricter requirements of GDPR, making it a dual-compliance consent management platform.

### Scope

This guide covers:

- GDPR vs DPDP comparison and key differences
- GDPR consent requirements and how ConsentChain meets them
- Data subject rights implementation (Articles 15-22)
- Legal bases for processing under GDPR
- Compliance checker usage and interpretation
- API endpoint documentation for GDPR operations
- Migration guide from DPDP-only to GDPR-compliant deployments

### Target Audience

- Data Protection Officers (DPOs)
- Compliance engineers
- Backend developers integrating GDPR endpoints
- System architects designing GDPR-compliant workflows
- Legal counsel evaluating technical controls

---

## Table of Contents

1. [GDPR vs DPDP Comparison](#1-gdpr-vs-dpdp-comparison)
2. [GDPR Consent Requirements](#2-gdpr-consent-requirements)
3. [Data Subject Rights Implementation](#3-data-subject-rights-implementation)
4. [Legal Bases for Processing](#4-legal-bases-for-processing)
5. [Compliance Checker Usage](#5-compliance-checker-usage)
6. [API Endpoints Documentation](#6-api-endpoints-documentation)
7. [Migration Guide: DPDP to GDPR](#7-migration-guide-dpdp-to-gdpr)
8. [International Data Transfers](#8-international-data-transfers)
9. [Data Breach Notification](#9-data-breach-notification)
10. [Records of Processing Activities](#10-records-of-processing-activities)
11. [Data Protection Impact Assessments](#11-data-protection-impact-assessments)
12. [Role of the Data Protection Officer](#12-role-of-the-data-protection-officer)

---

## 1. GDPR vs DPDP Comparison

While both the GDPR and India's DPDP Act 2023 share common roots in data protection principles, there are significant differences in scope, requirements, and enforcement.

### 1.1 Structural Comparison

| Aspect | GDPR (EU 2016/679) | DPDP Act 2023 (India) |
|---|---|---|
| **Territorial Scope** | Applies to processing of EU residents' data, regardless of where the processor is located | Applies to digital personal data processed in India, or processing outside India for profiling Indian residents |
| **Legal Bases** | 6 legal bases (Art. 6): consent, contract, legal obligation, vital interests, public task, legitimate interests | Primarily consent-based; deemed consent for specific purposes (Section 7) |
| **Consent Standard** | Freely given, specific, informed, unambiguous, explicit for special categories | Free, specific, informed, unconditional, unambiguous, with clear affirmative action |
| **Data Subject Rights** | 8 rights (access, rectification, erasure, restrict, portability, object, automated decisions, withdraw) | 4 core rights (access, correction, erasure, grievance redressal) |
| **Special Category Data** | Article 9: racial/ethnic, political, religious, trade union, genetic, biometric, health, sexual orientation | Sensitive personal data with enhanced protections (Section 9) |
| **Children's Data** | Age 16 (member states may lower to 13) | Always requires verifiable parental consent for minors |
| **Breach Notification** | 72 hours to supervisory authority | No specific timeline defined |
| **Data Portability** | Explicit right (Art. 20) with structured, machine-readable format | Implicit through consent revocation |
| **DPO Requirement** | Mandatory for public authorities, large-scale monitoring, special category data | Data Protection Board (government body), no individual DPO mandate |
| **Cross-border Transfers** | Adequacy decisions, SCCs, BCRs, derogations | Government-notified countries only |
| **Maximum Fines** | Up to €20M or 4% of global annual turnover | Up to ₹250 crore (~€28M) per violation |
| **Right to Object** | Explicit right to object to processing (Art. 21) | Not explicitly defined |
| **Automated Decisions** | Right not to be subject to solely automated decisions (Art. 22) | Not explicitly defined |

### 1.2 Key Differences for Implementation

#### Stricter Consent Requirements

GDPR consent is stricter than DPDP in several ways:

1. **Granularity**: GDPR requires granular consent — separate consent for each purpose. DPDP allows broader consent within stated purposes.
2. **Withdrawal**: GDPR requires that withdrawing consent be as easy as giving it. DPDP requires withdrawal but is less specific about ease.
3. **Pre-ticked boxes**: GDPR explicitly prohibits pre-ticked boxes. DPDP requires "clear affirmative action" but doesn't explicitly address pre-ticked boxes.
4. **Legitimate interests**: GDPR allows processing without consent under "legitimate interests." DPDP has "deemed consent" for specific purposes.

#### Expanded Rights

GDPR grants 3 additional rights beyond DPDP:

- **Right to data portability** (Art. 20): Users can receive their data in a structured, machine-readable format
- **Right to restrict processing** (Art. 18): Users can limit how their data is used without requesting erasure
- **Rights related to automated decision-making** (Art. 22): Users can challenge decisions made solely by algorithms

#### Breach Notification Timeline

GDPR's 72-hour notification window is one of the strictest in the world. DPDP does not specify a timeline, making GDPR compliance more operationally demanding.

### 1.3 Compliance Mapping Matrix

| ConsentChain Feature | DPDP Coverage | GDPR Coverage | Notes |
|---|---|---|---|
| Consent creation & verification | ✅ Full | ✅ Full | GDPR validator adds Art. 9 checks |
| Consent revocation | ✅ Full | ✅ Full | GDPR adds "easy withdrawal" requirement |
| Audit trail (Algorand) | ✅ Full | ✅ Full | Satisfies Art. 30 records requirement |
| Grievance management | ✅ Full | ⚠️ Partial | GDPR uses "data subject request" terminology |
| Guardian support (minors) | ✅ Full | ⚠️ Partial | GDPR age threshold varies by member state |
| Data deletion orchestration | ✅ Full | ✅ Full | GDPR has 6 specific grounds (Art. 17) |
| Data portability | ❌ Not in DPDP | ✅ Implemented | JSON export via API |
| Right to object | ❌ Not in DPDP | ✅ Implemented | API endpoint available |
| Legitimate interests assessment | ❌ Not applicable | ⚠️ Planned | LIA workflow in roadmap |
| DPO appointment tracking | ❌ Not applicable | ⚠️ Partial | Compliance checker validates |

---

## 2. GDPR Consent Requirements

GDPR Article 4(11) defines consent as:

> "any freely given, specific, informed and unambiguous indication of the data subject's wishes by which he or she, by a statement or by a clear affirmative action, signifies agreement to the processing of personal data relating to him or her"

### 2.1 The Six Pillars of GDPR Consent

#### 2.1.1 Freely Given (Recital 32, 43)

Consent must not be coerced or bundled with other terms.

**ConsentChain Implementation:**

- Each consent request is independent — not bundled with terms of service
- No "take it or leave it" consent patterns
- Users can withdraw consent without service degradation (except where consent is the sole legal basis)
- Power imbalance assessment for employer-employee relationships

```python
# Validation in GDPRConsentValidator
if is_bundled_consent(consent_request):
    violations.append(
        "Consent must not be bundled with other terms. "
        "Each processing purpose requires separate consent."
    )
```

#### 2.1.2 Specific (Recital 32)

Consent must be tied to a clearly defined purpose.

**ConsentChain Implementation:**

- Every consent record requires a specific `purpose` field (minimum 10 characters)
- Purpose is enumerated and auditable
- Blanket or vague consent requests are rejected

```python
# Purpose specificity check
if not purpose or len(purpose.strip()) < 10:
    violations.append(
        "Purpose must be specific and clearly stated (min 10 characters)"
    )
```

#### 2.1.3 Informed (Articles 13-14)

Data subjects must be provided with information before consent is given.

**ConsentChain Implementation:**

- Consent templates include all required informational elements:
  - Identity of the data controller (fiduciary)
  - Purpose of processing
  - Categories of personal data
  - Retention periods
  - Rights of the data subject
  - Contact details of the DPO (if applicable)
- Multi-language support via i18n system
- Template rendering in the user's preferred language

#### 2.1.4 Unambiguous (Recital 32)

Consent requires a clear affirmative action — silence or inactivity does not constitute consent.

**ConsentChain Implementation:**

- Explicit opt-in mechanism (no pre-ticked boxes)
- Cryptographic signature via Algorand wallet for consent confirmation
- Timestamp and blockchain anchoring of the consent action
- Clear UI flow requiring explicit user action

#### 2.1.5 Explicit (Article 9)

For special category data, consent must be explicit — a higher standard than regular consent.

**ConsentChain Implementation:**

```python
SPECIAL_CATEGORIES = [
    "racial_ethnic",
    "political",
    "religious",
    "trade_union",
    "genetic",
    "biometric",
    "health",
    "sexual_orientation",
]

# Check: special category data requires explicit consent
has_special = any(dt in cls.SPECIAL_CATEGORIES for dt in data_types)
if has_special and not explicit:
    violations.append(
        "Explicit consent required for special category data (GDPR Art. 9)"
    )
```

The `explicit` flag triggers:

- Separate consent screen with clear warning about special category data
- Additional confirmation step
- Enhanced audit logging
- Shorter default retention period

#### 2.1.6 Easy to Withdraw (Article 7(3))

> "The data subject shall have the right to withdraw his or her consent at any time. [...] It shall be as easy to withdraw as to give consent."

**ConsentChain Implementation:**

- One-click revocation via dashboard
- Instant on-chain recording of revocation
- Same authentication method used for granting can be used for withdrawing
- Automatic notification to all downstream data processors

### 2.2 Age Verification (Article 8)

GDPR sets the digital consent age at 16, but member states may lower it to as low as 13.

**ConsentChain Implementation:**

```python
# Age verification in consent validation
if age is not None:
    if age < 13:
        violations.append("Under 13: parental consent required (GDPR Art. 8)")
    elif age < 16:
        violations.append(
            "Age 13-16: parental consent may be required "
            "(varies by EU member state)"
        )
```

**Configuration:**

Set the age threshold per member state in environment configuration:

```bash
# EU Member State specific age of consent
GDPR_CHILD_AGE_THRESHOLD=16  # Default (can be lowered per member state)
GDPR_CHILD_AGE_GERMANY=16
GDPR_CHILD_AGE_UK=13
GDPR_CHILD_AGE_FRANCE=15
GDPR_CHILD_AGE_SPAIN=14
```

### 2.3 Consent Record Requirements

Every consent record under GDPR must contain:

| Field | Requirement | ConsentChain Field |
|---|---|---|
| **Who consented** | Data subject identity | `principal_id`, `wallet_address` |
| **What they consented to** | Specific purpose | `purpose` |
| **How they consented** | Method of consent | `consent_method` (wallet signature, WebAuthn, OAuth) |
| **When they consented** | Timestamp | `created_at`, blockchain timestamp |
| **What information was provided** | Privacy notice version | `template_version`, `privacy_notice_hash` |
| **Legal basis** | Art. 6 basis | `legal_basis` enum |
| **Special category flag** | Art. 9 indicator | `explicit` boolean |
| **Withdrawal status** | Current consent state | `status` (granted/revoked/expired) |

All consent records are immutably stored on the Algorand blockchain, providing a tamper-proof audit trail that satisfies GDPR's accountability principle (Article 5(2)).

---

## 3. Data Subject Rights Implementation

GDPR Chapter III (Articles 12-23) grants data subjects specific rights. ConsentChain implements each right through dedicated API endpoints and automated workflows.

### 3.1 Right of Access (Article 15)

**What it means:** Data subjects can request confirmation of whether their personal data is being processed and access to that data.

**Response timeline:** Within 1 month (extendable by 2 months for complex requests).

**ConsentChain Implementation:**

```bash
curl -X POST https://api.consentchain.io/api/v1/gdpr/data-subject-request \
  -H "X-API-Key: $FIDUCIARY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "principal_id": "usr_abc123",
    "right": "right_to_access",
    "details": {
      "include_consent_history": true,
      "include_audit_trail": true
    }
  }'
```

**What is returned:**

- All personal data held about the data subject
- Purposes of processing
- Categories of personal data
- Recipients or categories of recipients
- Retention periods
- Source of the data (if not collected from the data subject)
- Existence of automated decision-making (including profiling)

### 3.2 Right to Rectification (Article 16)

**What it means:** Data subjects can request correction of inaccurate personal data.

**Response timeline:** Within 1 month.

**ConsentChain Implementation:**

```python
result = handler.right_to_rectification(
    principal_id="usr_abc123",
    corrections={
        "email": "new_email@example.com",
        "name": "Updated Name"
    }
)
# Returns:
# {
#   "right": "right_to_rectification",
#   "principal_id": "usr_abc123",
#   "corrections": {"email": "...", "name": "..."},
#   "status": "pending",
#   "deadline": "2026-05-12T00:00:00+00:00"
# }
```

### 3.3 Right to Erasure — "Right to Be Forgotten" (Article 17)

**What it means:** Data subjects can request deletion of their personal data under specific grounds.

**Response timeline:** Within 1 month.

**Valid grounds under GDPR (stricter than DPDP):**

| Ground | Description | Example |
|---|---|---|
| `consent_withdrawn` | Consent withdrawn and no other legal basis applies | User revokes marketing consent |
| `data_no_longer_necessary` | Data no longer needed for original purpose | Expired consent for analytics |
| `objection_to_processing` | User objects and no overriding legitimate grounds | User objects to profiling |
| `unlawful_processing` | Data was processed unlawfully | Processing without valid legal basis |
| `legal_obligation` | Erasure required by EU or member state law | Court order |
| `child_information_services` | Data collected from a child for information society services | Social media account created at age 14 |

**ConsentChain Implementation:**

```bash
curl -X POST https://api.consentchain.io/api/v1/gdpr/data-subject-request \
  -H "X-API-Key: $FIDUCIARY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "principal_id": "usr_abc123",
    "right": "right_to_erasure",
    "details": {
      "grounds": ["consent_withdrawn", "data_no_longer_necessary"]
    }
  }'
```

The data deletion orchestrator (`api.deletion.DataDeletionOrchestrator`) manages the full lifecycle:

1. **Validation:** Verify the grounds are valid
2. **Scope identification:** Identify all systems holding the data
3. **Deletion execution:** Remove data from PostgreSQL, Redis, and flag on-chain records
4. **Processor notification:** Notify all downstream processors
5. **Confirmation:** Send confirmation to the data subject
6. **Audit logging:** Record the deletion in the audit trail

**Important:** On-chain consent records on Algorand cannot be deleted (blockchain immutability). Instead, they are marked as "revoked/erased" with a cryptographic pointer that renders the data inaccessible. This approach is documented in the privacy policy and is consistent with the EU Blockchain Observatory's guidance on GDPR and blockchain.

### 3.4 Right to Restrict Processing (Article 18)

**What it means:** Data subjects can request that processing of their data be limited (not deleted, but not actively processed).

**When it applies:**

- Data accuracy is contested (during verification period)
- Processing is unlawful but the user opposes erasure
- Data is no longer needed but required for legal claims
- User has objected to processing (pending verification of legitimate grounds)

**ConsentChain Implementation:**

```python
result = handler.right_to_restrict_processing(
    principal_id="usr_abc123",
    reason="data_accuracy_contested"
)
```

### 3.5 Right to Data Portability (Article 20)

**What it means:** Data subjects can receive their personal data in a structured, commonly used, and machine-readable format, and transmit it to another controller.

**Supported formats:**

- `json` (default) — Full JSON export
- `csv` — Tabular data for spreadsheet import
- `xml` — XML format for legacy system compatibility

**ConsentChain Implementation:**

```bash
curl -X POST https://api.consentchain.io/api/v1/gdpr/data-subject-request \
  -H "X-API-Key: $FIDUCIARY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "principal_id": "usr_abc123",
    "right": "right_to_portability",
    "details": {
      "format": "json"
    }
  }'
```

**Export structure:**

```json
{
  "right": "right_to_data_portability",
  "principal_id": "usr_abc123",
  "format": "json",
  "status": "pending",
  "deadline": "2026-05-12T00:00:00+00:00",
  "export": {
    "personal_data": { ... },
    "consent_records": [ ... ],
    "audit_trail": [ ... ],
    "metadata": {
      "generated_at": "2026-04-12T00:00:00Z",
      "format_version": "1.0",
      "total_records": 42
    }
  }
}
```

### 3.6 Right to Object (Article 21)

**What it means:** Data subjects can object to processing of their personal data, including profiling.

**ConsentChain Implementation:**

```bash
curl -X POST https://api.consentchain.io/api/v1/gdpr/data-subject-request \
  -H "X-API-Key: $FIDUCIARY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "principal_id": "usr_abc123",
    "right": "right_to_object",
    "details": {
      "reason": "I object to my data being used for profiling and automated decision-making"
    }
  }'
```

Processing must stop unless the controller demonstrates **compelling legitimate grounds** that override the data subject's interests.

### 3.7 Rights Related to Automated Decision-Making (Article 22)

**What it means:** Data subjects have the right not to be subject to a decision based solely on automated processing, including profiling, that produces legal effects or similarly significantly affects them.

**ConsentChain Implementation:**

- All automated decisions logged with explainability metadata
- Right to request human review of any automated decision
- AI/ML processing flagged in consent requests
- Opt-out mechanism available in dashboard

### 3.8 Rights Summary Table

| Right | Article | Endpoint | Timeline | Status |
|---|---|---|---|---|
| Access | Art. 15 | `POST /api/v1/gdpr/data-subject-request` | 1 month | ✅ Implemented |
| Rectification | Art. 16 | `POST /api/v1/gdpr/data-subject-request` | 1 month | ✅ Implemented |
| Erasure | Art. 17 | `POST /api/v1/gdpr/data-subject-request` | 1 month | ✅ Implemented |
| Restrict Processing | Art. 18 | `POST /api/v1/gdpr/data-subject-request` | 1 month | ✅ Implemented |
| Data Portability | Art. 20 | `POST /api/v1/gdpr/data-subject-request` | 1 month | ✅ Implemented |
| Object | Art. 21 | `POST /api/v1/gdpr/data-subject-request` | 1 month | ✅ Implemented |
| Automated Decisions | Art. 22 | `POST /api/v1/gdpr/data-subject-request` | 1 month | ✅ Implemented |
| Withdraw Consent | Art. 7(3) | `POST /api/v1/consent/revoke` | Immediate | ✅ Implemented |

---

## 4. Legal Bases for Processing

GDPR Article 6 provides six legal bases for processing personal data. Unlike DPDP, which is primarily consent-based, GDPR allows processing under multiple bases.

### 4.1 The Six Legal Bases

#### 4.1.1 Consent (Article 6(1)(a))

The data subject has given consent for processing for one or more specific purposes.

**When to use:**

- Marketing communications
- Optional analytics and profiling
- Processing of special category data (requires explicit consent under Art. 9)
- Any processing where no other basis applies

**ConsentChain Implementation:**

```python
legal_basis = GDPRLegalBasis.CONSENT
retention_days = 365  # Default retention for consent-based processing
```

#### 4.1.2 Contract (Article 6(1)(b))

Processing is necessary for the performance of a contract with the data subject.

**When to use:**

- Processing user data to provide the consent management service
- Billing and payment processing
- Account management

**ConsentChain Implementation:**

```python
legal_basis = GDPRLegalBasis.CONTRACT
retention_days = 730  # Longer retention for contractual obligations
```

#### 4.1.3 Legal Obligation (Article 6(1)(c))

Processing is necessary for compliance with a legal obligation.

**When to use:**

- Tax reporting
- Regulatory compliance (e.g., DPDP Act, GDPR itself)
- Court orders and law enforcement requests

**ConsentChain Implementation:**

```python
legal_basis = GDPRLegalBasis.LEGAL_OBLIGATION
retention_days = 2555  # 7 years — longest retention for legal compliance
```

#### 4.1.4 Vital Interests (Article 6(1)(d))

Processing is necessary to protect the vital interests of the data subject or another person.

**When to use:**

- Emergency medical situations
- Life-threatening scenarios

**Note:** This is rarely applicable in the context of a consent management platform.

```python
legal_basis = GDPRLegalBasis.VITAL_INTERESTS
retention_days = 365
```

#### 4.1.5 Public Task (Article 6(1)(e))

Processing is necessary for the performance of a task carried out in the public interest or in the exercise of official authority.

**When to use:**

- Government or regulatory bodies using ConsentChain
- Public health monitoring

```python
legal_basis = GDPRLegalBasis.PUBLIC_TASK
retention_days = 730
```

#### 4.1.6 Legitimate Interests (Article 6(1)(f))

Processing is necessary for the legitimate interests of the controller or a third party, except where overridden by the data subject's interests.

**When to use:**

- Fraud prevention
- Network and information security
- Internal administrative purposes

**Requires:** A Legitimate Interests Assessment (LIA) documenting the balancing test.

```python
legal_basis = GDPRLegalBasis.LEGITIMATE_INTERESTS
retention_days = 365
```

### 4.2 Legal Basis Decision Tree

```
Is the data subject giving explicit consent?
├── Yes → Use CONSENT (Art. 6(1)(a))
│   └── Is it special category data (Art. 9)?
│       ├── Yes → Require explicit consent + additional safeguards
│       └── No → Standard consent flow
│
├── No → Is processing necessary for a contract?
│   ├── Yes → Use CONTRACT (Art. 6(1)(b))
│   └── No → Is there a legal obligation?
│       ├── Yes → Use LEGAL_OBLIGATION (Art. 6(1)(c))
│       └── No → Is it a matter of vital interests?
│           ├── Yes → Use VITAL_INTERESTS (Art. 6(1)(d))
│           └── No → Is it a public task?
│               ├── Yes → Use PUBLIC_TASK (Art. 6(1)(e))
│               └── No → Can legitimate interests apply?
│                   ├── Yes → Use LEGITIMATE_INTERESTS (Art. 6(1)(f))
│                   │   └── Have you completed a Legitimate Interests Assessment?
│                   │       ├── Yes → Proceed with documented LIA
│                   │       └── No → Complete LIA before processing
│                   └── No → Cannot process — seek consent or legal advice
```

### 4.3 Special Category Data (Article 9)

Processing of special category data requires **both** a legal basis under Article 6 **and** a condition under Article 9.

| Special Category | Example | ConsentChain Handling |
|---|---|---|
| Racial or ethnic origin | Demographic surveys | `explicit: true` required |
| Political opinions | Political preference data | `explicit: true` required |
| Religious beliefs | Religious affiliation | `explicit: true` required |
| Trade union membership | Union membership records | `explicit: true` required |
| Genetic data | DNA test results | `explicit: true` required |
| Biometric data | Fingerprint, facial recognition | `explicit: true` required |
| Health data | Medical records, disability status | `explicit: true` required |
| Sexual orientation | LGBTQ+ status | `explicit: true` required |

**Validation:**

```bash
curl -X POST https://api.consentchain.io/api/v1/gdpr/validate-consent \
  -H "X-API-Key: $FIDUCIARY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "purpose": "Health research study participation and data analysis",
    "data_types": ["health", "genetic"],
    "legal_basis": "consent",
    "explicit": true,
    "age": 35
  }'
```

---

## 5. Compliance Checker Usage

The `GDPRComplianceChecker` provides automated assessment of GDPR compliance posture for any registered fiduciary.

### 5.1 Running a Compliance Check

```bash
curl -X GET https://api.consentchain.io/api/v1/gdpr/compliance-status/fid_abc123 \
  -H "X-API-Key: $FIDUCIARY_API_KEY"
```

### 5.2 Response Format

```json
{
  "success": true,
  "message": "GDPR compliance score: 70.0% - Good",
  "data": {
    "framework": "GDPR",
    "fiduciary_id": "fid_abc123",
    "score": 70.0,
    "total_checks": 10,
    "passed_checks": 7,
    "failed_checks": 3,
    "checks": {
      "consent_valid": true,
      "privacy_policy_present": true,
      "dpo_appointed": false,
      "data_protection_impact_assessment": false,
      "breach_notification_procedure": true,
      "data_processing_records": false,
      "international_transfers_documented": true,
      "data_subject_rights_process": true,
      "data_minimization": true,
      "purpose_limitation": true
    },
    "recommendations": [
      "Implement: Data Protection Officer appointed",
      "Implement: DPIA conducted for high-risk processing",
      "Implement: Records of processing activities maintained"
    ],
    "compliance_level": "Good"
  }
}
```

### 5.3 Compliance Levels

| Score Range | Level | Action Required |
|---|---|---|
| 90-100% | **Excellent** | Maintain current controls; continuous monitoring |
| 70-89% | **Good** | Address failed checks within 30 days |
| 50-69% | **Partial** | Priority remediation required; legal review recommended |
| 0-49% | **Non-Compliant** | Immediate action required; consider suspending processing |

### 5.4 Compliance Check Details

| Check | Description | GDPR Reference | Verification Method |
|---|---|---|---|
| `consent_valid` | GDPR-compliant consent mechanism | Art. 4(11), Art. 7 | API validation endpoint |
| `privacy_policy_present` | Clear privacy policy provided | Art. 13-14 | URL accessibility check |
| `dpo_appointed` | Data Protection Officer appointed | Art. 37-39 | DPO contact in registry |
| `data_protection_impact_assessment` | DPIA for high-risk processing | Art. 35 | DPIA document in registry |
| `breach_notification_procedure` | 72-hour breach notification | Art. 33-34 | Procedure documentation |
| `data_processing_records` | Records of processing activities | Art. 30 | RoPA documentation |
| `international_transfers_documented` | Transfer mechanisms documented | Art. 44-49 | SCCs or adequacy decisions |
| `data_subject_rights_process` | Process for handling rights requests | Art. 12-22 | Automated workflow test |
| `data_minimization` | Data minimization applied | Art. 5(1)(c) | Data type analysis |
| `purpose_limitation` | Purpose limitation respected | Art. 5(1)(b) | Purpose verification |

### 5.5 Automated Compliance Monitoring

The compliance checker can be integrated into CI/CD pipelines:

```yaml
# .github/workflows/gdpr-compliance.yml
- name: GDPR Compliance Check
  run: |
    RESPONSE=$(curl -s https://api.consentchain.io/api/v1/gdpr/compliance-status/$FIDUCIARY_ID \
      -H "X-API-Key: $FIDUCIARY_API_KEY")
    SCORE=$(echo $RESPONSE | jq -r '.data.score')
    if (( $(echo "$SCORE < 70" | bc -l) )); then
      echo "GDPR compliance score below threshold: $SCORE%"
      exit 1
    fi
    echo "GDPR compliance score: $SCORE% - PASS"
```

---

## 6. API Endpoints Documentation

All GDPR-specific endpoints are prefixed with `/api/v1/gdpr`. Authentication requires a valid fiduciary API key via the `X-API-Key` header.

### 6.1 Validate GDPR Consent

**Endpoint:** `POST /api/v1/gdpr/validate-consent`

**Rate Limit:** 100 requests/minute

**Authentication:** Fiduciary API key required

**Purpose:** Validate that a consent request meets GDPR requirements before processing.

**Request Schema:**

```json
{
  "purpose": "string (min 10 chars) — Specific purpose for data processing",
  "data_types": ["string array — Categories of personal data"],
  "legal_basis": "string — One of: consent, contract, legal_obligation, vital_interests, public_task, legitimate_interests",
  "explicit": "boolean (default: false) — Whether explicit consent is required for special category data (Art. 9)",
  "age": "integer (optional, 0-150) — Data subject age for age verification (Art. 8)"
}
```

**Response Schema:**

```json
{
  "success": true,
  "message": "Consent is GDPR compliant",
  "data": {
    "valid": true,
    "violations": [],
    "retention_days": 365,
    "legal_basis": "consent"
  }
}
```

**Example — Valid Consent:**

```bash
curl -X POST https://api.consentchain.io/api/v1/gdpr/validate-consent \
  -H "X-API-Key: your_fiduciary_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "purpose": "Newsletter subscription and marketing communications",
    "data_types": ["identity", "contact"],
    "legal_basis": "consent",
    "explicit": false,
    "age": 25
  }'
```

**Example — Invalid Consent (Special Category Without Explicit Flag):**

```bash
curl -X POST https://api.consentchain.io/api/v1/gdpr/validate-consent \
  -H "X-API-Key: your_fiduciary_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "purpose": "Medical research participation",
    "data_types": ["health", "genetic"],
    "legal_basis": "consent",
    "explicit": false
  }'
```

Response:

```json
{
  "success": false,
  "message": "Consent violations found",
  "data": {
    "valid": false,
    "violations": [
      "Explicit consent required for special category data (GDPR Art. 9)"
    ],
    "retention_days": 365,
    "legal_basis": "consent"
  }
}
```

### 6.2 Handle Data Subject Request

**Endpoint:** `POST /api/v1/gdpr/data-subject-request`

**Rate Limit:** 20 requests/minute

**Authentication:** Fiduciary API key required

**Purpose:** Register and process GDPR data subject rights requests.

**Request Schema:**

```json
{
  "principal_id": "string — Data subject identifier",
  "right": "string — One of: right_to_access, right_to_erasure, right_to_portability, right_to_object",
  "details": "object (optional) — Additional details specific to the right being exercised"
}
```

**Supported Rights and Details:**

| Right | Details Fields |
|---|---|
| `right_to_access` | `include_consent_history`, `include_audit_trail` |
| `right_to_erasure` | `grounds` (array of valid grounds) |
| `right_to_portability` | `format` (json, csv, xml) |
| `right_to_object` | `reason` (string) |

### 6.3 Get Compliance Status

**Endpoint:** `GET /api/v1/gdpr/compliance-status/{fiduciary_id}`

**Authentication:** Fiduciary API key required

**Purpose:** Get GDPR compliance score and detailed assessment for a fiduciary.

**Response:** See Section 5.2 for response format.

### 6.4 List Legal Bases

**Endpoint:** `GET /api/v1/gdpr/legal-bases`

**Authentication:** None (public endpoint)

**Purpose:** List all valid GDPR legal bases for processing and special category data types.

**Response:**

```json
{
  "success": true,
  "message": "GDPR legal bases for processing",
  "data": {
    "legal_bases": [
      {"basis": "consent", "description": "Consent", "article": "Art. 6(1)"},
      {"basis": "contract", "description": "Contract", "article": "Art. 6(1)"},
      {"basis": "legal_obligation", "description": "Legal Obligation", "article": "Art. 6(1)"},
      {"basis": "vital_interests", "description": "Vital Interests", "article": "Art. 6(1)"},
      {"basis": "public_task", "description": "Public Task", "article": "Art. 6(1)"},
      {"basis": "legitimate_interests", "description": "Legitimate Interests", "article": "Art. 6(1)"}
    ],
    "special_categories": [
      "racial_ethnic", "political", "religious", "trade_union",
      "genetic", "biometric", "health", "sexual_orientation"
    ],
    "note": "Special categories require explicit consent (Art. 9)"
  }
}
```

### 6.5 Error Responses

| Status Code | Description |
|---|---|
| `400` | Invalid request — validation errors, unsupported right |
| `401` | Unauthorized — missing or invalid API key |
| `404` | Fiduciary not found |
| `429` | Rate limit exceeded |
| `500` | Internal server error |

---

## 7. Migration Guide: DPDP to GDPR

This guide walks through the steps to extend a DPDP-only ConsentChain deployment to full GDPR compliance.

### 7.1 Prerequisites

- ConsentChain v1.0.0 or later with GDPR module enabled
- Existing DPDP-compliant deployment
- Access to fiduciary configuration dashboard
- Legal review of privacy policy for GDPR requirements

### 7.2 Step 1: Enable GDPR Module

The GDPR module is included in ConsentChain but may need explicit activation.

**Configuration:**

```bash
# .env or .env.production
GDPR_ENABLED=true
GDPR_COMPLIANCE_MODE=strict  # Options: strict, advisory
GDPR_DEFAULT_LEGAL_BASIS=consent
```

**Verify activation:**

```bash
curl https://api.consentchain.io/api/v1/gdpr/legal-bases
```

Should return the 6 legal bases and 8 special categories.

### 7.3 Step 2: Update Consent Templates

DPDP consent templates need to be updated for GDPR-specific requirements.

**Changes required:**

| DPDP Template | GDPR Addition |
|---|---|
| Purpose statement | Add legal basis (Art. 6) |
| Data types list | Flag special categories (Art. 9) |
| Retention period | Align with GDPR-specific periods |
| Rights statement | Expand from 4 DPDP rights to 8 GDPR rights |
| Contact information | Add DPO contact details (if applicable) |
| International transfers | Add transfer mechanism documentation |

**Template update via API:**

```bash
curl -X POST https://api.consentchain.io/api/v1/templates \
  -H "X-API-Key: $FIDUCIARY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GDPR Marketing Consent",
    "category": "marketing",
    "language": "en",
    "fields": {
      "legal_basis": "consent",
      "purpose": "Marketing communications and promotional offers",
      "data_types": ["identity", "contact"],
      "retention_days": 365,
      "special_categories": [],
      "rights_notice": "You have the right to access, rectify, erase, restrict, port, and object to processing of your data."
    },
    "compliance_frameworks": ["dpdp", "gdpr"]
  }'
```

### 7.4 Step 3: Update Data Retention Policies

GDPR retention periods differ from DPDP defaults.

| Legal Basis | DPDP Default | GDPR Default | Action |
|---|---|---|---|
| Consent | 365 days | 365 days | ✅ No change |
| Contract | 365 days | 730 days | ⚠️ Update |
| Legal Obligation | 365 days | 2555 days (7 years) | ⚠️ Update |
| Legitimate Interests | N/A | 365 days | ➕ New |

**Update retention configuration:**

```python
# In your fiduciary configuration
RETENTION_POLICY = {
    "consent": 365,
    "contract": 730,
    "legal_obligation": 2555,
    "legitimate_interests": 365,
}
```

### 7.5 Step 4: Implement Data Subject Rights Workflows

GDPR adds 3 rights not covered by DPDP. Configure workflows for each:

**Right to Data Portability:**

- Configure export format (JSON, CSV, XML)
- Set up automated data collection pipeline
- Define delivery mechanism (download link, email attachment)

**Right to Object:**

- Configure processing categories that can be objected to
- Set up legitimate interests balancing test workflow
- Define appeal process for contested objections

**Right to Restrict Processing:**

- Define restriction states in data lifecycle
- Configure notification to downstream processors
- Set up periodic review of restricted data

### 7.6 Step 5: Appoint a Data Protection Officer (if required)

Under GDPR Article 37, a DPO is mandatory if:

- Processing is carried out by a public authority
- Core activities require regular and systematic monitoring of data subjects on a large scale
- Core activities involve large-scale processing of special category data

**Register DPO in ConsentChain:**

```bash
curl -X PUT https://api.consentchain.io/api/v1/fiduciary/$FIDUCIARY_ID/dpo \
  -H "X-API-Key: $FIDUCIARY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Smith",
    "email": "dpo@company.eu",
    "phone": "+49 30 12345678",
    "address": "Privacy Street 1, 10115 Berlin, Germany"
  }'
```

### 7.7 Step 6: Run Compliance Assessment

After completing the above steps, run the compliance checker:

```bash
curl https://api.consentchain.io/api/v1/gdpr/compliance-status/$FIDUCIARY_ID \
  -H "X-API-Key: $FIDUCIARY_API_KEY"
```

Target a minimum score of **70%** (Good) before going live with GDPR processing.

### 7.8 Step 7: Update Privacy Policy

Your privacy policy must be updated to include:

- Identity and contact details of the controller
- Contact details of the DPO (if appointed)
- Purposes and legal basis for each processing activity
- Recipients or categories of recipients
- International transfer mechanisms
- Retention periods
- Data subject rights (all 8)
- Right to lodge a complaint with a supervisory authority
- Whether providing data is a statutory or contractual requirement

### 7.9 Step 8: Test Data Subject Request Handling

Before going live, test each data subject right:

```bash
# Test right to access
curl -X POST https://api.consentchain.io/api/v1/gdpr/data-subject-request \
  -H "X-API-Key: $FIDUCIARY_API_KEY" \
  -d '{"principal_id": "test_user_1", "right": "right_to_access"}'

# Test right to erasure
curl -X POST https://api.consentchain.io/api/v1/gdpr/data-subject-request \
  -H "X-API-Key: $FIDUCIARY_API_KEY" \
  -d '{"principal_id": "test_user_2", "right": "right_to_erasure", "details": {"grounds": ["consent_withdrawn"]}}'

# Test right to portability
curl -X POST https://api.consentchain.io/api/v1/gdpr/data-subject-request \
  -H "X-API-Key: $FIDUCIARY_API_KEY" \
  -d '{"principal_id": "test_user_3", "right": "right_to_portability", "details": {"format": "json"}}'

# Test right to object
curl -X POST https://api.consentchain.io/api/v1/gdpr/data-subject-request \
  -H "X-API-Key: $FIDUCIARY_API_KEY" \
  -d '{"principal_id": "test_user_4", "right": "right_to_object", "details": {"reason": "Testing objection workflow"}}'
```

### 7.10 Migration Checklist

- [ ] GDPR module enabled in configuration
- [ ] Consent templates updated with GDPR fields
- [ ] Legal basis documented for each processing activity
- [ ] Special category data flagged with explicit consent
- [ ] Data retention periods aligned with GDPR defaults
- [ ] Data portability workflow configured
- [ ] Right to object workflow configured
- [ ] Right to restrict processing workflow configured
- [ ] DPO appointed (if required)
- [ ] Privacy policy updated
- [ ] Compliance score ≥ 70%
- [ ] All data subject rights tested
- [ ] Breach notification procedure documented
- [ ] Records of Processing Activities (RoPA) created
- [ ] International transfer mechanisms documented
- [ ] Staff training completed on GDPR requirements

---

## 8. International Data Transfers

GDPR Chapter V (Articles 44-49) regulates transfers of personal data outside the EU/EEA.

### 8.1 Transfer Mechanisms

| Mechanism | Description | ConsentChain Support |
|---|---|---|
| **Adequacy Decision** | EU Commission determined the country provides adequate protection | Automatic — no additional safeguards needed |
| **Standard Contractual Clauses (SCCs)** | EU-approved contractual provisions | ✅ Documented in compliance checker |
| **Binding Corporate Rules (BCRs)** | Internal rules for multinational companies | ⚠️ Requires manual documentation |
| **Derogations** | Specific situations (explicit consent, contract performance) | ✅ Available per-consent |

### 8.2 Algorand Blockchain Considerations

Since ConsentChain stores consent records on the Algorand blockchain, which is a global distributed network, data is technically replicated across nodes worldwide. The consent record hash on-chain does not contain personal data — only cryptographic hashes and metadata. Full personal data remains in the PostgreSQL database, which can be geographically restricted.

**Recommended configuration:**

```bash
# Restrict database to EU region
DATABASE_REGION=eu-west-1
DATABASE_URL=postgresql+asyncpg://user:password@eu-db.consentchain.io:5432/consentchain

# Enable IPFS pinning in EU-only nodes
IPFS_GATEWAY=https://eu-ipfs.consentchain.io/ipfs/
```

---

## 9. Data Breach Notification

GDPR Article 33 requires notification to the supervisory authority within **72 hours** of becoming aware of a personal data breach.

### 9.1 ConsentChain Breach Response Workflow

1. **Detection:** Automated monitoring via Sentry, Prometheus alerts
2. **Assessment:** Determine if breach affects personal data
3. **Notification:** Alert DPO and compliance team via event bus
4. **Documentation:** Record breach in audit trail (Algorand-anchored)
5. **Authority notification:** If risk to rights and freedoms, notify within 72 hours
6. **Data subject notification:** If high risk, notify affected individuals (Art. 34)

### 9.2 Breach Categories

| Risk Level | Authority Notification | Data Subject Notification | Timeline |
|---|---|---|---|
| **No risk** | Not required | Not required | Document internally |
| **Risk to rights** | Required | Not required | 72 hours |
| **High risk** | Required | Required | 72 hours + without undue delay |

---

## 10. Records of Processing Activities

GDPR Article 30 requires controllers and processors to maintain records of processing activities (RoPA).

### 10.1 Required Records

| Record | Description | ConsentChain Location |
|---|---|---|
| Controller identity | Name and contact details | Fiduciary registry |
| Processing purposes | Why data is processed | Consent purpose field |
| Data categories | Types of personal data | Consent data_types |
| Recipient categories | Who receives the data | Webhook subscriptions |
| Transfer documentation | International transfer safeguards | Compliance checker |
| Retention periods | How long data is kept | Retention policy config |
| Security measures | Technical and organizational measures | Security audit reports |

### 10.2 Generating RoPA Report

```bash
curl -X POST https://api.consentchain.io/api/v1/compliance/report \
  -H "X-API-Key: $FIDUCIARY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "ropa",
    "fiduciary_id": "fid_abc123",
    "framework": "gdpr",
    "format": "pdf"
  }'
```

---

## 11. Data Protection Impact Assessments

GDPR Article 35 requires a Data Protection Impact Assessment (DPIA) when processing is likely to result in a high risk to the rights and freedoms of data subjects.

### 11.1 When is a DPIA Required?

- Systematic and extensive evaluation of personal aspects (profiling)
- Large-scale processing of special category data
- Systematic monitoring of a publicly accessible area
- New technologies where risk is uncertain

### 11.2 DPIA Checklist

- [ ] Describe the processing operations and purposes
- [ ] Assess necessity and proportionality
- [ ] Assess risks to rights and freedoms
- [ ] Identify measures to address risks
- [ ] Consult with DPO
- [ ] Document the assessment
- [ ] Review and update regularly

**ConsentChain tracks DPIA status in the compliance checker under `data_protection_impact_assessment`.**

---

## 12. Role of the Data Protection Officer

Under GDPR Articles 37-39, the DPO has specific responsibilities:

### 12.1 DPO Responsibilities

1. **Inform and advise** the controller/processor of GDPR obligations
2. **Monitor compliance** with GDPR and internal policies
3. **Provide advice** on DPIAs and monitor their performance
4. **Cooperate with supervisory authorities**
5. **Act as contact point** for supervisory authorities and data subjects

### 12.2 DPO Independence

The DPO must:

- Not receive instructions regarding the performance of their tasks
- Not be dismissed or penalized for performing their tasks
- Report directly to the highest management level
- Have adequate resources to perform their tasks

### 12.3 DPO Registration in ConsentChain

```bash
# Register DPO contact
curl -X PUT https://api.consentchain.io/api/v1/fiduciary/$FIDUCIARY_ID/dpo \
  -H "X-API-Key: $FIDUCIARY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Smith",
    "email": "dpo@company.eu",
    "phone": "+49 30 12345678",
    "address": "Privacy Street 1, 10115 Berlin, Germany"
  }'
```

The compliance checker validates DPO appointment as part of the overall GDPR compliance score.

---

## Appendix A: GDPR Articles Referenced

| Article | Topic | ConsentChain Coverage |
|---|---|---|
| Art. 4(11) | Definition of consent | ✅ |
| Art. 5 | Principles of processing | ✅ |
| Art. 6 | Lawfulness of processing | ✅ |
| Art. 7 | Conditions for consent | ✅ |
| Art. 8 | Child consent | ✅ |
| Art. 9 | Special category data | ✅ |
| Art. 12 | Transparent information | ✅ |
| Art. 13-14 | Information to be provided | ✅ |
| Art. 15 | Right of access | ✅ |
| Art. 16 | Right to rectification | ✅ |
| Art. 17 | Right to erasure | ✅ |
| Art. 18 | Right to restrict processing | ✅ |
| Art. 20 | Right to data portability | ✅ |
| Art. 21 | Right to object | ✅ |
| Art. 22 | Automated decision-making | ✅ |
| Art. 30 | Records of processing | ✅ |
| Art. 33-34 | Breach notification | ✅ |
| Art. 35 | DPIA | ✅ |
| Art. 37-39 | DPO | ✅ |
| Art. 44-49 | International transfers | ✅ |

## Appendix B: Environment Variables

| Variable | Description | Default | Required for GDPR |
|---|---|---|---|
| `GDPR_ENABLED` | Enable GDPR compliance module | `false` | Yes |
| `GDPR_COMPLIANCE_MODE` | `strict` or `advisory` | `advisory` | Recommended |
| `GDPR_DEFAULT_LEGAL_BASIS` | Default legal basis | `consent` | Yes |
| `GDPR_CHILD_AGE_THRESHOLD` | Age of digital consent | `16` | Yes |
| `GDPR_DPO_EMAIL` | DPO contact email | — | If DPO required |
| `DATABASE_REGION` | Database geographic region | — | For data residency |
| `IPFS_GATEWAY` | IPFS gateway URL | `https://ipfs.io/ipfs/` | EU-only for GDPR |

## Appendix C: Quick Reference Commands

```bash
# Validate consent
curl -X POST https://api.consentchain.io/api/v1/gdpr/validate-consent \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"purpose": "...", "data_types": [...], "legal_basis": "consent"}'

# Submit data subject request
curl -X POST https://api.consentchain.io/api/v1/gdpr/data-subject-request \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"principal_id": "...", "right": "right_to_access"}'

# Check compliance score
curl https://api.consentchain.io/api/v1/gdpr/compliance-status/$FIDUCIARY_ID \
  -H "X-API-Key: $KEY"

# List legal bases
curl https://api.consentchain.io/api/v1/gdpr/legal-bases
```

---

*Last updated: April 2026 | Document version: 1.0 | ConsentChain v1.0.0*
*For questions about GDPR compliance, contact your Data Protection Officer or the ConsentChain support team.*
