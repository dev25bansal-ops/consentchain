# ConsentChain Quick Start Guide

Get ConsentChain running in 5 minutes.

## Prerequisites

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 14+ (or use Docker)
- Redis 7+ (or use Docker)

## Option 1: Docker Compose (Recommended)

```bash
# Clone repository
git clone <repo-url>
cd consentchain

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env

# Start all services
docker-compose up -d

# Wait for services to be ready
sleep 15

# Verify installation
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs
```

## Option 2: Local Development

### Backend

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env

# Start PostgreSQL and Redis (if not using Docker)
# PostgreSQL: createdb consentchain
# Redis: should be running on port 6379

# Run migrations
alembic upgrade head

# Start development server
uvicorn api.main:app --reload --port 8000
```

### Frontend (Dashboard)

```bash
cd dashboard-v2

# Install dependencies
npm install

# Start development server
npm run dev
```

### Frontend (Admin Portal)

```bash
cd admin-portal

# Install dependencies
npm install

# Start development server
npm run dev
```

## Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# View interactive API docs
open http://localhost:8000/docs

# Run tests
pytest tests/ -v
```

## First Steps

### 1. Register a Data Fiduciary (Enterprise)

```bash
curl -X POST http://localhost:8000/api/v1/fiduciary/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Company",
    "registration_number": "REG123456",
    "wallet_address": "YOUR_ALGORAND_ADDRESS",
    "contact_email": "admin@mycompany.com",
    "data_categories": ["identity", "contact"],
    "purposes": ["service", "marketing"]
  }'
```

Save the returned `api_key` - you'll need it for authenticated requests.

### 2. Create a Consent Record

```bash
curl -X POST http://localhost:8000/api/v1/consent/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "principal_wallet": "USER_WALLET_ADDRESS",
    "purpose": "service",
    "data_types": ["identity"],
    "duration_days": 90
  }'
```

### 3. Verify Consent

```bash
curl -X POST http://localhost:8000/api/v1/consent/verify \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "consent_id": "CONSENT_ID_FROM_PREVIOUS_STEP"
  }'
```

## Common Issues

### Database connection refused
Make sure PostgreSQL is running and DATABASE_URL in .env is correct.

### Redis connection timeout
Ensure Redis is running on port 6379 (or update REDIS_URL in .env).

### Algorand network errors
Check ALGORAND_NETWORK and MASTER_ADDRESS in .env. For local development, TESTING=true will skip blockchain calls.

### Port already in use
Change the port in docker-compose.yml or stop the service using that port.

## Next Steps

- Read the [API Reference](docs/API_REFERENCE.md)
- Review [Architecture Decision Records](docs/adr/)
- Check [Deployment Guide](docs/DEPLOYMENT.md)
- Join our [Community](link-to-community)

## Support

- Documentation: [docs/](docs/)
- Issues: [GitHub Issues](link-to-issues)
- Email: support@consentchain.io
