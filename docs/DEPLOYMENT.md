# Deployment Guide

## Prerequisites

- Docker and Docker Compose
- Python 3.10+
- Algorand Testnet Account with funded ALGOs
- PostgreSQL (or use Docker)
- Redis (or use Docker)

## Quick Start (Docker)

### 1. Clone and Configure

```bash
# Clone the repository
git clone https://github.com/your-org/consentchain.git
cd consentchain

# Copy environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 2. Generate Algorand Account

```bash
# Install py-algorand-sdk
pip install py-algorand-sdk

# Generate new account
python -c "
from algosdk import account, mnemonic
private_key, address = account.generate_account()
mnemonic_phrase = mnemonic.from_private_key(private_key)
print(f'Address: {address}')
print(f'Mnemonic: {mnemonic_phrase}')
print()
print('IMPORTANT: Save the mnemonic securely!')
"

# Fund the account using Testnet Dispenser:
# https://testnet.algoexplorer.io/dispenser
```

### 3. Update .env File

```env
# Algorand Configuration
ALGORAND_NODE_URL=https://testnet-api.algonode.cloud
ALGORAND_INDEXER_URL=https://testnet-idx.algonode.cloud
ALGORAND_NETWORK=testnet
MASTER_MNEMONIC=your_25_word_mnemonic_phrase_here

# Database
DATABASE_URL=postgresql+asyncpg://consentchain:password@postgres:5432/consentchain
REDIS_URL=redis://redis:6379/0

# Security
API_SECRET_KEY=generate_a_secure_random_key_here
JWT_SECRET=generate_another_secure_key_here

# Application
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
LOG_LEVEL=INFO
```

### 4. Generate Secure Keys

```bash
# Generate API secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 5. Start Services

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f api
```

### 6. Deploy Smart Contracts

```bash
# Wait for services to be healthy
docker-compose ps

# Deploy contracts
docker-compose exec api python scripts/deploy_contracts.py
```

### 7. Initialize Database

```bash
# Run migrations
docker-compose exec api alembic upgrade head
```

### 8. Access Services

| Service   | URL                          | Description    |
| --------- | ---------------------------- | -------------- |
| API       | http://localhost:8000        | REST API       |
| Dashboard | http://localhost:3000        | User Dashboard |
| API Docs  | http://localhost:8000/docs   | Swagger UI     |
| Health    | http://localhost:8000/health | Health Check   |

---

## Manual Deployment (Without Docker)

### 1. Install Dependencies

```bash
# Using Poetry (recommended)
poetry install

# Or using pip
pip install -r requirements.txt
```

### 2. Set Up PostgreSQL

```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib
sudo -u postgres psql

# Create database and user
CREATE DATABASE consentchain;
CREATE USER consentchain WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE consentchain TO consentchain;

# Exit psql
\q
```

### 3. Set Up Redis

```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

### 4. Configure Environment

```bash
# Copy and edit .env
cp .env.example .env
nano .env

# Update DATABASE_URL for local PostgreSQL
DATABASE_URL=postgresql+asyncpg://consentchain:your_password@localhost:5432/consentchain
```

### 5. Run Database Migrations

```bash
# Initialize Alembic (if not already done)
alembic init api/migrations

# Run migrations
alembic upgrade head
```

### 6. Deploy Smart Contracts

```bash
# Make sure your account is funded
python scripts/deploy_contracts.py
```

### 7. Start API Server

```bash
# Development
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Production (using Gunicorn)
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 8. Serve Dashboard

```bash
# Development
cd dashboard
python -m http.server 3000

# Production (using nginx)
sudo apt-get install nginx
sudo cp nginx.conf /etc/nginx/sites-available/consentchain
sudo ln -s /etc/nginx/sites-available/consentchain /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

---

## Production Deployment

### 1. Infrastructure Requirements

| Component | Minimum   | Recommended |
| --------- | --------- | ----------- |
| CPU       | 2 cores   | 4 cores     |
| RAM       | 4 GB      | 8 GB        |
| Storage   | 50 GB SSD | 100 GB SSD  |
| Network   | 10 Mbps   | 100 Mbps    |

### 2. SSL/TLS Configuration

```nginx
# /etc/nginx/sites-available/consentchain
server {
    listen 443 ssl http2;
    server_name api.consentchain.io;

    ssl_certificate /etc/letsencrypt/live/consentchain.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/consentchain.io/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 443 ssl http2;
    server_name consentchain.io;

    ssl_certificate /etc/letsencrypt/live/consentchain.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/consentchain.io/privkey.pem;

    location / {
        root /var/www/consentchain/dashboard;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.consentchain.io consentchain.io;
    return 301 https://$server_name$request_uri;
}
```

### 3. Obtain SSL Certificate

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d consentchain.io -d api.consentchain.io

# Auto-renewal
sudo systemctl enable certbot.timer
```

### 4. Systemd Service

```ini
# /etc/systemd/system/consentchain-api.service
[Unit]
Description=ConsentChain API Server
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=consentchain
Group=consentchain
WorkingDirectory=/opt/consentchain
Environment="PATH=/opt/consentchain/.venv/bin"
ExecStart=/opt/consentchain/.venv/bin/gunicorn api.main:app \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    -b 127.0.0.1:8000 \
    --access-logfile /var/log/consentchain/access.log \
    --error-logfile /var/log/consentchain/error.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable consentchain-api
sudo systemctl start consentchain-api
```

### 5. Database Backup

```bash
# Daily backup cron job
crontab -e

# Add daily backup at 2 AM
0 2 * * * pg_dump -U consentchain consentchain > /backup/consentchain_$(date +\%Y\%m\%d).sql

# Keep only last 30 days
0 3 * * * find /backup -name "consentchain_*.sql" -mtime +30 -delete
```

---

## Monitoring

### 1. Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/health/database

# Redis health
curl http://localhost:8000/health/redis
```

### 2. Logging

```python
# Configure logging in .env
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/consentchain/app.log
```

### 3. Prometheus Metrics (Optional)

```yaml
# docker-compose.yml addition
prometheus:
  image: prom/prometheus
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana
  ports:
    - "3001:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
version: "3.8"

services:
  api:
    deploy:
      replicas: 4
      resources:
        limits:
          cpus: "1"
          memory: 1G
        reservations:
          cpus: "0.5"
          memory: 512M

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.scale.conf:/etc/nginx/nginx.conf
    depends_on:
      - api
```

### Load Balancer Configuration

```nginx
# nginx.scale.conf
upstream consentchain_backend {
    least_conn;
    server api-1:8000 weight=5;
    server api-2:8000 weight=5;
    server api-3:8000 weight=5;
    server api-4:8000 weight=5;
}

server {
    listen 80;

    location / {
        proxy_pass http://consentchain_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Security Checklist

### Pre-Deployment

- [ ] Change all default passwords
- [ ] Generate new API and JWT secrets
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS for production domains only
- [ ] Set up firewall rules
- [ ] Enable rate limiting
- [ ] Configure logging
- [ ] Set up backup automation
- [ ] Review DPDP compliance checklist

### Firewall Rules

```bash
# UFW configuration
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Secret Management

```bash
# Using HashiCorp Vault (recommended for production)
# Or use environment variables with secure storage

# Never commit secrets to git
echo ".env" >> .gitignore
echo "*.key" >> .gitignore
echo "*.pem" >> .gitignore
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection
psql -h localhost -U consentchain -d consentchain

# Check logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

#### 2. Redis Connection Failed

```bash
# Check Redis status
sudo systemctl status redis

# Test connection
redis-cli ping
```

#### 3. Smart Contract Deployment Failed

```bash
# Check account balance
python -c "
from algosdk.v2client import algod
from algosdk import account, mnemonic
import os

client = algod.AlgodClient('', 'https://testnet-api.algonode.cloud')
mnemonic_phrase = os.getenv('MASTER_MNEMONIC')
private_key = mnemonic.to_private_key(mnemonic_phrase)
address = account.address_from_private_key(private_key)
info = client.account_info(address)
print(f'Address: {address}')
print(f'Balance: {info[\"amount\"] / 1_000_000} ALGO')
"

# Fund account if needed
# https://testnet.algoexplorer.io/dispenser
```

#### 4. API Not Responding

```bash
# Check API logs
docker-compose logs api

# Check port availability
sudo netstat -tulpn | grep 8000

# Restart API
docker-compose restart api
```

---

## Maintenance

### Database Maintenance

```bash
# Weekly vacuum analyze
crontab -e
0 4 * * 0 psql -U consentchain -d consentchain -c "VACUUM ANALYZE;"

# Monthly reindex
0 4 1 * * psql -U consentchain -d consentchain -c "REINDEX DATABASE consentchain;"
```

### Log Rotation

```bash
# /etc/logrotate.d/consentchain
/var/log/consentchain/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 consentchain consentchain
    sharedscripts
    postrotate
        systemctl reload consentchain-api > /dev/null
    endscript
}
```

---

## Upgrading

### 1. Backup

```bash
# Backup database
pg_dump -U consentchain consentchain > backup_$(date +%Y%m%d).sql

# Backup environment
cp .env .env.backup
```

### 2. Pull Updates

```bash
git pull origin main
```

### 3. Update Dependencies

```bash
poetry install
```

### 4. Run Migrations

```bash
alembic upgrade head
```

### 5. Restart Services

```bash
docker-compose down
docker-compose up -d
```

---

## Support

For issues or questions:

- GitHub Issues: https://github.com/your-org/consentchain/issues
- Documentation: https://docs.consentchain.io
- Email: support@consentchain.io
