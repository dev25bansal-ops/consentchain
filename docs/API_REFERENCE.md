# API Reference

## Base URL

```
Production: https://api.consentchain.io/api/v1
Testnet:    https://testnet.consentchain.io/api/v1
Local:      http://localhost:8000/api/v1
```

## Authentication

### Data Fiduciary API Key

Include in request header:

```
Authorization: Bearer cc_your_api_key_here
```

### Data Principal JWT

Obtain via wallet authentication:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Endpoints

### Health Check

**GET** `/health`

Check API status.

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

---

### Register Data Fiduciary

**POST** `/api/v1/fiduciary/register`

Register a new Data Fiduciary entity.

**Request Body:**

```json
{
  "name": "Example Fintech Pvt Ltd",
  "registration_number": "U72200KA2021PTC123456",
  "contact_email": "dpo@examplefintech.com",
  "data_categories": ["PERSONAL_INFO", "CONTACT_INFO", "FINANCIAL_DATA"],
  "purposes": ["SERVICE_DELIVERY", "PAYMENT_PROCESSING"]
}
```

**Response:**

```json
{
  "success": true,
  "message": "Fiduciary registered successfully",
  "data": {
    "fiduciary_id": "550e8400-e29b-41d4-a716-446655440000",
    "api_key": "cc_AbCdEfGhIjKlMnOpQrStUvWxYz123456",
    "note": "Store the API key securely. It will not be shown again."
  }
}
```

---

### Create Consent

**POST** `/api/v1/consent/create`

Record a new consent on-chain.

**Headers:**

- `Authorization: Bearer <api_key>` (Fiduciary auth)

**Request Body:**

```json
{
  "principal_wallet": "7JOPJA6L2JJ7K4K3JQ7J7V2K2N2L2M2N2L2M2N2L2M2N2L2M2N2L2M2N",
  "fiduciary_id": "550e8400-e29b-41d4-a716-446655440000",
  "purpose": "MARKETING",
  "data_types": ["PERSONAL_INFO", "CONTACT_INFO"],
  "duration_days": 90,
  "metadata": {
    "source": "mobile_app",
    "version": "2.1.0"
  },
  "signature": "ed25519_signature_hex"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Consent created successfully",
  "data": {
    "consent_id": "660e8400-e29b-41d4-a716-446655440001",
    "status": "GRANTED",
    "granted_at": "2024-01-01T10:00:00Z",
    "expires_at": "2024-04-01T10:00:00Z",
    "on_chain_tx_id": "ABC123DEF456GHI789JKL012MNO345PQR678",
    "consent_hash": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2"
  }
}
```

---

### Batch Create Consents

**POST** `/api/v1/consent/batch`

Create multiple consents in a single request.

**Headers:**

- `Authorization: Bearer <api_key>` (Fiduciary auth)

**Request Body:**

```json
{
  "batch_id": "batch_2024_01_01_001",
  "consents": [
    {
      "principal_wallet": "ADDRESS_1",
      "fiduciary_id": "550e8400-e29b-41d4-a716-446655440000",
      "purpose": "MARKETING",
      "data_types": ["PERSONAL_INFO"],
      "duration_days": 90,
      "metadata": {},
      "signature": "sig1"
    },
    {
      "principal_wallet": "ADDRESS_2",
      "fiduciary_id": "550e8400-e29b-41d4-a716-446655440000",
      "purpose": "SERVICE_DELIVERY",
      "data_types": ["PERSONAL_INFO", "CONTACT_INFO"],
      "duration_days": 365,
      "metadata": {},
      "signature": "sig2"
    }
  ]
}
```

**Response:**

```json
{
  "success": true,
  "message": "Batch processed: 2/2 consents created",
  "data": {
    "batch_id": "batch_2024_01_01_001",
    "results": [
      {
        "principal_wallet": "ADDRESS_1",
        "consent_id": "consent_id_1",
        "success": true
      },
      {
        "principal_wallet": "ADDRESS_2",
        "consent_id": "consent_id_2",
        "success": true
      }
    ]
  }
}
```

---

### Revoke Consent

**POST** `/api/v1/consent/revoke`

Revoke an existing consent.

**Headers:**

- `Authorization: Bearer <jwt_token>` (Principal auth)

**Request Body:**

```json
{
  "consent_id": "660e8400-e29b-41d4-a716-446655440001",
  "reason": "No longer want promotional emails",
  "signature": "ed25519_signature_hex"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Consent revoked successfully",
  "data": {
    "consent_id": "660e8400-e29b-41d4-a716-446655440001",
    "status": "REVOKED",
    "revoked_at": "2024-02-15T14:30:00Z"
  }
}
```

---

### Modify Consent

**POST** `/api/v1/consent/modify`

Modify an existing consent's parameters.

**Headers:**

- `Authorization: Bearer <jwt_token>` (Principal auth)

**Request Body:**

```json
{
  "consent_id": "660e8400-e29b-41d4-a716-446655440001",
  "new_purpose": "ANALYTICS",
  "new_duration_days": 180,
  "reason": "Changing from marketing to analytics",
  "signature": "ed25519_signature_hex"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Consent modified successfully",
  "data": {
    "consent_id": "660e8400-e29b-41d4-a716-446655440001",
    "status": "MODIFIED",
    "updated_at": "2024-02-15T14:35:00Z"
  }
}
```

---

### Verify Consent

**POST** `/api/v1/consent/verify`

Verify if a consent is valid and active.

**Headers:**

- `Authorization: Bearer <api_key>` (Fiduciary auth)

**Request Body:**

```json
{
  "consent_id": "660e8400-e29b-41d4-a716-446655440001",
  "principal_id": "550e8400-e29b-41d4-a716-446655440002"
}
```

**Response (Valid):**

```json
{
  "success": true,
  "message": "Consent verified",
  "data": {
    "valid": true,
    "consent_id": "660e8400-e29b-41d4-a716-446655440001",
    "principal_id": "550e8400-e29b-41d4-a716-446655440002",
    "fiduciary_id": "550e8400-e29b-41d4-a716-446655440000",
    "purpose": "MARKETING",
    "data_types": ["PERSONAL_INFO", "CONTACT_INFO"],
    "granted_at": "2024-01-01T10:00:00Z",
    "expires_at": "2024-04-01T10:00:00Z",
    "on_chain_tx_id": "ABC123DEF456GHI789JKL012MNO345PQR678",
    "consent_hash": "a1b2c3d4..."
  }
}
```

**Response (Invalid):**

```json
{
  "success": false,
  "message": "Consent revoked",
  "data": {
    "valid": false,
    "reason": "Consent revoked",
    "revoked_at": "2024-02-15T14:30:00Z"
  }
}
```

---

### Query Consents

**GET** `/api/v1/consent/query`

Query consents with filters.

**Headers:**

- `Authorization: Bearer <api_key>` (Fiduciary auth)

**Query Parameters:**

- `principal_id` (optional): Filter by principal UUID
- `fiduciary_id` (optional): Filter by fiduciary UUID
- `status` (optional): Filter by status (GRANTED, REVOKED, EXPIRED)
- `purpose` (optional): Filter by purpose
- `from_date` (optional): Filter from date (ISO 8601)
- `to_date` (optional): Filter to date (ISO 8601)
- `page` (optional): Page number (default: 1)
- `limit` (optional): Results per page (default: 20, max: 100)

**Example Request:**

```
GET /api/v1/consent/query?status=GRANTED&purpose=MARKETING&page=1&limit=20
```

**Response:**

```json
{
  "success": true,
  "message": "Found 45 consents",
  "data": {
    "consents": [
      {
        "consent_id": "660e8400-e29b-41d4-a716-446655440001",
        "principal_id": "550e8400-e29b-41d4-a716-446655440002",
        "fiduciary_id": "550e8400-e29b-41d4-a716-446655440000",
        "purpose": "MARKETING",
        "data_types": ["PERSONAL_INFO", "CONTACT_INFO"],
        "status": "GRANTED",
        "granted_at": "2024-01-01T10:00:00Z",
        "expires_at": "2024-04-01T10:00:00Z",
        "consent_hash": "a1b2c3d4..."
      }
    ],
    "page": 1,
    "limit": 20,
    "total": 45
  }
}
```

---

### Get Consent History

**GET** `/api/v1/consent/{consent_id}/history`

Get all events for a consent.

**Headers:**

- `Authorization: Bearer <jwt_token>` (Principal auth)

**Response:**

```json
{
  "success": true,
  "message": "Found 3 events",
  "data": {
    "events": [
      {
        "event_id": "770e8400-e29b-41d4-a716-446655440001",
        "event_type": "CONSENT_GRANTED",
        "actor": "7JOPJA6L2JJ7K4K3JQ7J7V2K2N2L2M2N...",
        "actor_type": "principal",
        "previous_status": null,
        "new_status": "GRANTED",
        "tx_id": "ABC123DEF456GHI789JKL012MNO345PQR678",
        "created_at": "2024-01-01T10:00:00Z"
      },
      {
        "event_id": "770e8400-e29b-41d4-a716-446655440002",
        "event_type": "CONSENT_MODIFIED",
        "actor": "7JOPJA6L2JJ7K4K3JQ7J7V2K2N2L2M2N...",
        "actor_type": "principal",
        "previous_status": "GRANTED",
        "new_status": "MODIFIED",
        "tx_id": "DEF456GHI789JKL012MNO345PQR678ABC123",
        "created_at": "2024-02-15T14:35:00Z"
      },
      {
        "event_id": "770e8400-e29b-41d4-a716-446655440003",
        "event_type": "CONSENT_REVOKED",
        "actor": "7JOPJA6L2JJ7K4K3JQ7J7V2K2N2L2M2N...",
        "actor_type": "principal",
        "previous_status": "MODIFIED",
        "new_status": "REVOKED",
        "tx_id": "GHI789JKL012MNO345PQR678ABC123DEF456",
        "created_at": "2024-03-01T09:00:00Z"
      }
    ]
  }
}
```

---

### Query Audit Logs

**POST** `/api/v1/audit/query`

Query audit trail logs.

**Headers:**

- `Authorization: Bearer <api_key>` (Fiduciary auth)

**Request Body:**

```json
{
  "fiduciary_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "CONSENT_GRANTED",
  "from_date": "2024-01-01T00:00:00Z",
  "to_date": "2024-01-31T23:59:59Z",
  "page": 1,
  "limit": 50
}
```

**Response:**

```json
{
  "success": true,
  "message": "Found 125 audit logs",
  "data": {
    "logs": [
      {
        "log_id": "880e8400-e29b-41d4-a716-446655440001",
        "action": "CONSENT_CREATED",
        "resource_type": "consent",
        "resource_id": "660e8400-e29b-41d4-a716-446655440001",
        "on_chain_reference": "ABC123DEF456GHI789JKL012MNO345PQR678",
        "created_at": "2024-01-01T10:00:00Z"
      }
    ]
  }
}
```

---

### Generate Merkle Root

**POST** `/api/v1/audit/merkle-root`

Generate and anchor Merkle root on-chain.

**Headers:**

- `Authorization: Bearer <api_key>` (Fiduciary auth)

**Request Body:**

```json
{
  "event_ids": [
    "770e8400-e29b-41d4-a716-446655440001",
    "770e8400-e29b-41d4-a716-446655440002",
    "770e8400-e29b-41d4-a716-446655440003"
  ]
}
```

**Response:**

```json
{
  "success": true,
  "message": "Merkle root generated and anchored on-chain",
  "data": {
    "merkle_root": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2",
    "tx_id": "MNO345PQR678ABC123DEF456GHI789JKL012",
    "event_count": 3
  }
}
```

---

### Generate Compliance Report

**POST** `/api/v1/compliance/report`

Generate DPDP compliance report.

**Headers:**

- `Authorization: Bearer <api_key>` (Fiduciary auth)

**Request Body:**

```json
{
  "fiduciary_id": "550e8400-e29b-41d4-a716-446655440000",
  "period_start": "2024-01-01T00:00:00Z",
  "period_end": "2024-03-31T23:59:59Z"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Compliance report generated",
  "data": {
    "report_id": "990e8400-e29b-41d4-a716-446655440001",
    "fiduciary_id": "550e8400-e29b-41d4-a716-446655440000",
    "period_start": "2024-01-01T00:00:00Z",
    "period_end": "2024-03-31T23:59:59Z",
    "total_consents": 1000,
    "active_consents": 850,
    "revoked_consents": 100,
    "expired_consents": 50,
    "sensitive_data_consents": 150,
    "third_party_sharing_count": 75,
    "audit_events": 2500,
    "compliance_score": 95,
    "on_chain_hash": "b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2"
  }
}
```

---

### Get Compliance Status

**GET** `/api/v1/compliance/status/{fiduciary_id}`

Get current compliance status and checklist.

**Headers:**

- `Authorization: Bearer <api_key>` (Fiduciary auth)

**Response:**

```json
{
  "success": true,
  "message": "Compliance status retrieved",
  "data": {
    "fiduciary_id": "550e8400-e29b-41d4-a716-446655440000",
    "compliance_score": 95,
    "last_report_date": "2024-03-31T23:59:59Z",
    "compliance_checklist": [
      { "item": "Consent request clearly states purpose", "required": true },
      { "item": "Data categories explicitly listed", "required": true },
      { "item": "Consent duration specified", "required": true },
      { "item": "Right to revoke clearly communicated", "required": true },
      { "item": "Grievance redressal mechanism provided", "required": true },
      { "item": "Data retention policy disclosed", "required": true },
      { "item": "Third-party sharing disclosure", "required": true },
      { "item": "Consent withdrawal mechanism available", "required": true }
    ]
  }
}
```

---

## Error Responses

### 400 Bad Request

```json
{
  "success": false,
  "message": "Invalid request: duration_days must be between 1 and 365"
}
```

### 401 Unauthorized

```json
{
  "detail": "Invalid API key"
}
```

### 404 Not Found

```json
{
  "success": false,
  "message": "Consent not found"
}
```

### 500 Internal Server Error

```json
{
  "success": false,
  "message": "Internal server error"
}
```

---

## Rate Limits

| Endpoint          | Rate Limit  |
| ----------------- | ----------- |
| `/consent/create` | 100/minute  |
| `/consent/batch`  | 10/minute   |
| `/consent/verify` | 1000/minute |
| `/consent/query`  | 500/minute  |
| `/audit/query`    | 100/minute  |
| `/compliance/*`   | 10/minute   |

---

## WebSocket Events (Future)

Real-time consent events via WebSocket:

```javascript
const ws = new WebSocket("wss://api.consentchain.io/ws");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Event:", data.event_type, data.consent_id);
};
```

Event types:

- `consent.granted`
- `consent.revoked`
- `consent.modified`
- `consent.expired`
