# ConsentChain

**DPDP Act Compliant Consent Management on Algorand**

ConsentChain is a foundational compliance infrastructure module that streamlines adherence to India's Digital Personal Data Protection (DPDP) Act using blockchain technology.

## Problem Statement

The enforcement of India's Digital Personal Data Protection (DPDP) Act has created an urgent and mandatory compliance challenge for all enterprises acting as "Data Fiduciaries." The core problems addressed:

1. **Absence of secure, transparent, tamper-proof consent recording mechanism**
2. **Opaque centralized solutions prone to data manipulation**
3. **No immutable audit trails for regulatory scrutiny**
4. **Data Principals lack verifiable control over their data**

## Solution Architecture

### Two-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                             │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  User Dashboard │ Enterprise SDK  │   Compliance API            │
│ (Data Principal)│(Data Fiduciary) │   (Regulators)              │
└─────────────────┴─────────────────┴─────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OFF-CHAIN API LAYER                          │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  REST API       │  Database       │   Cryptographic Services    │
│  (FastAPI)      │  (PostgreSQL)   │   (Hash/Sign/Verify)        │
└─────────────────┴─────────────────┴─────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ON-CHAIN LAYER (ALGORAND)                    │
├─────────────────┬───────────────────────────────────────────────┤
│ Consent Registry│ Audit Trail Contract                           │
│ Smart Contract  │ (Merkle Root Storage)                         │
└─────────────────┴───────────────────────────────────────────────┘
```

### Key Features

- **Immutable Consent Registry**: On-chain recording of consent events (grant, revoke, modify)
- **Data Minimization**: Only cryptographic hashes stored on-chain
- **Transparent Audit Trails**: Merkle tree-based verification of event history
- **Real-time Verification**: API endpoints for instant consent validation
- **User Dashboard**: Data Principals can view and manage all consents
- **Enterprise SDK**: Plug-and-play integration for Data Fiduciaries

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Algorand Testnet Account (for testing)
- Poetry (recommended) or pip

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/consentchain.git
cd consentchain

# Install dependencies with Poetry
poetry install

# Or with pip
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
```

### Configuration

Edit `.env` with your settings:

```env
# Algorand Configuration
ALGORAND_NODE_URL=https://testnet-api.algonode.cloud
ALGORAND_INDEXER_URL=https://testnet-idx.algonode.cloud
ALGORAND_NETWORK=testnet

# Master Account (generate a new one for testing)
MASTER_MNEMONIC=your_25_word_mnemonic_here

# API Configuration
API_SECRET_KEY=your_secure_api_secret_key_here
JWT_SECRET=your_jwt_secret_key_here

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/consentchain
```

### Deploy Smart Contracts

```bash
# Fund your deployer account using Algorand Testnet Dispenser
# https://testnet.algoexplorer.io/dispenser

# Deploy contracts
python scripts/deploy_contracts.py
```

### Run the API Server

```bash
# Start PostgreSQL
docker run -d --name consentchain-db \
  -e POSTGRES_USER=consentchain \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=consentchain \
  -p 5432:5432 \
  postgres:14

# Run migrations
alembic upgrade head

# Start the API
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Run the Dashboard

```bash
# Serve the dashboard
cd dashboard
python -m http.server 3000

# Open http://localhost:3000 in your browser
```

## API Documentation

### Authentication

All API endpoints require authentication:

- **Data Fiduciaries**: API Key in `Authorization: Bearer <api_key>` header
- **Data Principals**: JWT token in `Authorization: Bearer <jwt_token>` header

### Core Endpoints

#### Create Consent

```http
POST /api/v1/consent/create
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "principal_wallet": "ALGORAND_ADDRESS_58_CHARS",
  "fiduciary_id": "uuid",
  "purpose": "MARKETING",
  "data_types": ["PERSONAL_INFO", "CONTACT_INFO"],
  "duration_days": 90,
  "signature": "ed25519_signature"
}
```

#### Verify Consent

```http
POST /api/v1/consent/verify
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "consent_id": "uuid",
  "principal_id": "uuid"
}
```

#### Revoke Consent

```http
POST /api/v1/consent/revoke
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
  "consent_id": "uuid",
  "reason": "Optional reason for revocation",
  "signature": "ed25519_signature"
}
```

#### Query Consents

```http
GET /api/v1/consent/query?principal_id=uuid&status=GRANTED&page=1&limit=20
Authorization: Bearer <api_key>
```

#### Generate Compliance Report

```http
POST /api/v1/compliance/report
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "fiduciary_id": "uuid",
  "period_start": "2024-01-01T00:00:00Z",
  "period_end": "2024-12-31T23:59:59Z"
}
```

## SDK Usage

### Python SDK

```python
from sdk.client import ConsentChainClient, ConsentPurpose, DataType

# Initialize client
client = ConsentChainClient(
    api_url="http://localhost:8000",
    api_key="your_api_key",
    fiduciary_id="your_fiduciary_id"
)

# Create consent
consent = client.create_consent(
    principal_wallet="ALGORAND_ADDRESS",
    purpose=ConsentPurpose.MARKETING.value,
    data_types=[DataType.PERSONAL_INFO.value, DataType.CONTACT_INFO.value],
    duration_days=90
)

# Verify consent
result = client.verify_consent(consent.consent_id)
if result.valid:
    print("Consent is valid!")
else:
    print(f"Consent invalid: {result.reason}")

# Check consent before action
result = client.check_consent_before_action(
    principal_id="user_uuid",
    purpose="MARKETING",
    data_types=["PERSONAL_INFO"]
)

# Generate compliance report
report = client.generate_compliance_report(
    period_start=datetime(2024, 1, 1),
    period_end=datetime(2024, 12, 31)
)
print(f"Compliance Score: {report['compliance_score']}")
```

### Using Consent Middleware

```python
from sdk.client import ConsentMiddleware

middleware = ConsentMiddleware(
    api_url="http://localhost:8000",
    api_key="your_api_key",
    fiduciary_id="your_fiduciary_id"
)

# Decorator pattern
@middleware.verify("user_id", "MARKETING", ["PERSONAL_INFO"])
def send_marketing_email(user_id):
    # This will only execute if consent is valid
    pass

# Or manual verification
def process_user_data(user_id):
    result = middleware.client.check_consent_before_action(
        user_id, "SERVICE_DELIVERY", ["PERSONAL_INFO"]
    )
    if not result.valid:
        raise PermissionError(f"No consent: {result.reason}")
    # Process data...
```

## Smart Contract Architecture

### Consent Registry Contract

The `ConsentRegistry` smart contract manages consent lifecycle:

```python
# Local State (per user)
principal_address: bytes  # Data Principal's wallet
fiduciary_address: bytes  # Data Fiduciary's wallet
purpose: bytes           # Purpose of data use
data_types_hash: bytes   # Hash of data categories
status: uint64          # 0=Pending, 1=Granted, 2=Revoked, 3=Expired
granted_at: uint64      # Block round when granted
expires_at: uint64      # Block round when expires
consent_hash: bytes     # Unique consent identifier

# Global State
total_consents: uint64
active_consents: uint64
revoked_consents: uint64
admin_address: bytes
```

### Audit Trail Contract

The `AuditTrail` contract maintains immutable event logs:

```python
# Global State
event_counter: uint64    # Total events logged
merkle_root: bytes      # Current Merkle tree root
last_event_hash: bytes  # Previous event hash
admin_address: bytes    # Authorized auditor

# Operations
log_event: Record single event
batch_log: Record multiple events with Merkle root
get_root: Query current Merkle root
verify_proof: Verify event inclusion
```

## DPDP Act Compliance

### Key Requirements Addressed

| DPDP Requirement      | ConsentChain Feature                      |
| --------------------- | ----------------------------------------- |
| Clear consent request | API returns purpose, data types, duration |
| Right to withdraw     | Dashboard allows instant revocation       |
| Data minimization     | Only hashes stored on-chain               |
| Audit trail           | Merkle-tree verified event history        |
| Grievance redressal   | Complete event history accessible         |
| Cross-border transfer | Third-party sharing tracked explicitly    |

### Sensitive Data Categories

The system recognizes all sensitive data categories under DPDP:

- Financial data
- Health data
- Biometric data
- Caste or tribe
- Religious beliefs
- Political opinions
- Genetic data

## Security Considerations

### Data Privacy

- **No PII on-chain**: Only cryptographic hashes stored
- **Email/Phone hashed**: Cannot be reversed from blockchain
- **Consent signatures**: Ed25519 cryptographic signatures

### Smart Contract Security

- **Access control**: Only consent owner can revoke/modify
- **State validation**: Status transitions enforced
- **Event integrity**: Merkle proofs for verification

### API Security

- **API Key authentication**: Secure fiduciary access
- **JWT tokens**: User session management
- **Rate limiting**: Prevent abuse

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_crypto.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

## Deployment

### Docker Deployment

```bash
# Build Docker image
docker build -t consentchain:latest .

# Run with Docker Compose
docker-compose up -d
```

### Production Checklist

1. Use Mainnet instead of Testnet
2. Secure master mnemonic (HSM recommended)
3. Enable TLS for API endpoints
4. Configure proper CORS origins
5. Set up database backups
6. Implement rate limiting
7. Configure logging and monitoring
8. Set up alerting for contract events

## Roadmap

- [ ] Mobile app for Data Principals
- [ ] Multi-signature consent for joint accounts
- [ ] Automated consent expiry notifications
- [ ] Integration with major Indian fintech platforms
- [ ] Zero-knowledge proofs for enhanced privacy
- [ ] Cross-chain compatibility

## License

MIT License - See LICENSE file for details.

## Support

For support, please open an issue on GitHub or contact support@consentchain.io

---

Built with ❤️ for AlgoBharat Hack Series 3.0
