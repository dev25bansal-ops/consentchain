#!/bin/bash

echo "========================================"
echo "ConsentChain - Development Setup Script"
echo "========================================"

echo ""
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

echo ""
echo "Installing dependencies..."
if command -v poetry &> /dev/null; then
    echo "Using Poetry..."
    poetry install
else
    echo "Poetry not found, using pip..."
    pip install -r requirements.txt || pip install pyteal py-algorand-sdk fastapi uvicorn pydantic python-dotenv cryptography pyjwt httpx redis sqlalchemy asyncpg alembic passlib python-multipart jinja2
fi

echo ""
echo "Setting up environment..."
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo "Please edit .env with your configuration!"
else
    echo ".env already exists, skipping..."
fi

echo ""
echo "Creating necessary directories..."
mkdir -p logs

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Edit .env with your Algorand mnemonic and other settings"
echo "2. Start PostgreSQL: docker-compose up -d postgres"
echo "3. Run migrations: alembic upgrade head"
echo "4. Deploy contracts: python scripts/deploy_contracts.py"
echo "5. Start API: uvicorn api.main:app --reload"
echo "6. Open dashboard: http://localhost:3000"
echo ""
