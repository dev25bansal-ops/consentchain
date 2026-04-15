# ConsentChain Makefile
# DPDP Act Compliant Consent Management on Algorand
# Version: 1.1.0

.PHONY: help install test lint format type-check migrate dev dev-hot docker docker-prod deploy backup clean seed db-reset contracts-deploy

# Default target
help: ## Show this help message
	@echo "ConsentChain - DPDP Act Compliant Consent Management"
	@echo "====================================================="
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================
# Installation & Setup
# ============================================

install: ## Install all dependencies (Python + Node.js)
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "Installing development dependencies..."
	pip install -e ".[dev]" 2>/dev/null || true
	@echo "Installing admin-portal dependencies..."
	cd admin-portal && npm install 2>/dev/null || echo "Skipping admin-portal (npm not available)"
	@echo "Installation complete!"

install-poetry: ## Install dependencies using Poetry
	@echo "Installing with Poetry..."
	poetry install --with dev
	@echo "Poetry installation complete!"

# ============================================
# Testing
# ============================================

test: ## Run all tests
	@pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage report
	@pytest tests/ -v --cov=api --cov=core --cov=contracts --cov=contracts_v2 --cov-report=term-missing --cov-report=html:htmlcov

test-unit: ## Run unit tests only
	@pytest tests/unit/ -v -m "not slow and not integration"

test-integration: ## Run integration tests only
	@pytest tests/integration/ -v -m "integration"

test-slow: ## Run slow tests only
	@pytest tests/ -v -m "slow"

test-watch: ## Run tests in watch mode (pytest-watch)
	@pytest tests/ --tb=short -f

# ============================================
# Code Quality
# ============================================

lint: ## Run linters (ruff + mypy)
	@echo "Running ruff..."
	ruff check api/ core/ sdk/ contracts/ contracts_v2/ tests/
	@echo "Running mypy..."
	mypy api/ core/ sdk/
	@echo "Linting complete!"

lint-fix: ## Run linters and auto-fix issues
	@echo "Running ruff with auto-fix..."
	ruff check --fix api/ core/ sdk/ contracts/ contracts_v2/ tests/
	@echo "Running ruff format..."
	ruff format api/ core/ sdk/ contracts/ contracts_v2/ tests/
	@echo "Lint-fix complete!"

format: ## Format code with black and ruff
	@echo "Formatting code..."
	black api/ core/ sdk/ contracts/ contracts_v2/ tests/
	ruff format api/ core/ sdk/ contracts/ contracts_v2/ tests/
	@echo "Formatting complete!"

type-check: ## Run type checking with mypy
	@mypy api/ core/ sdk/ --ignore-missing-imports

quality: lint format test ## Run full quality checks (lint + format + test)

# ============================================
# Database
# ============================================

migrate: ## Run database migrations
	@echo "Running Alembic migrations..."
	alembic upgrade head
	@echo "Migrations complete!"

migrate-status: ## Show migration status
	alembic current
	alembic history --verbose

migrate-revision: ## Create a new migration revision
	@read -p "Enter migration message: " msg; alembic revision --autogenerate -m "$$msg"

db-reset: ## Reset database (DANGER: deletes all data!)
	@echo "WARNING: This will delete all data in the database!"
	@read -p "Are you sure? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		alembic downgrade base; \
		alembic upgrade head; \
		echo "Database reset complete!"; \
	else \
		echo "Aborted."; \
	fi

seed: ## Seed database with test data
	@echo "Seeding database with test data..."
	python scripts/seed_data.py
	@echo "Seeding complete!"

# ============================================
# Development
# ============================================

dev: ## Start development server
	@echo "Starting development server..."
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

dev-hot: ## Start development server with hot reload and OpenAPI docs
	@echo "Starting development server with hot reload..."
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug --access-log

dev-prod: ## Start production-like server locally
	@echo "Starting production-like server..."
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level info

# ============================================
# Docker
# ============================================

docker: ## Start with Docker Compose (development)
	@echo "Starting with Docker Compose..."
	docker-compose up --build

docker-detach: ## Start with Docker Compose in detached mode
	docker-compose up -d --build

docker-logs: ## View Docker logs
	docker-compose logs -f

docker-down: ## Stop Docker Compose
	docker-compose down

docker-clean: ## Stop Docker Compose and remove volumes
	docker-compose down -v

docker-prod: ## Start with production Docker Compose
	docker-compose -f docker-compose.prod.yml up --build

# ============================================
# Deployment
# ============================================

deploy: ## Deploy to production
	@echo "Deploying to production..."
	@echo "1. Running tests..."
	pytest tests/ -v --tb=short
	@echo "2. Building Docker image..."
	docker build -t consentchain:latest .
	@echo "3. Pushing to registry..."
	@echo "   (Configure your registry in CI/CD)"
	@echo "4. Deploying to Kubernetes..."
	kubectl apply -f k8s/ --record
	@echo "5. Waiting for rollout..."
	kubectl rollout status deployment/consentchain-api -n consentchain
	@echo "Deployment complete!"

deploy-rollback: ## Rollback last deployment
	@echo "Rolling back deployment..."
	kubectl rollout undo deployment/consentchain-api -n consentchain
	kubectl rollout status deployment/consentchain-api -n consentchain
	@echo "Rollback complete!"

deploy-status: ## Check deployment status
	kubectl get pods -n consentchain
	kubectl get svc -n consentchain
	kubectl get ingress -n consentchain

contracts-deploy: ## Deploy smart contracts
	@echo "Deploying smart contracts..."
	python scripts/deploy_contracts.py

# ============================================
# Backup & Maintenance
# ============================================

backup: ## Create database backup
	@echo "Creating database backup..."
	@mkdir -p backups
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	pg_dump -h $${DB_HOST:-localhost} -U $${DB_USER:-user} -d $${DB_NAME:-consentchain} \
		--format=custom --compress=9 \
		-f "backups/consentchain_$${TIMESTAMP}.dump" 2>/dev/null || \
	echo "Note: pg_dump not available. Using SQLite backup if applicable."
	@echo "Backup complete!"

backup-config: ## Backup configuration files
	@echo "Backing up configuration..."
	@mkdir -p backups
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	tar czf "backups/config_$${TIMESTAMP}.tar.gz" \
		.env docker-compose.yml docker-compose.prod.yml nginx.conf alembic.ini 2>/dev/null || true
	@echo "Configuration backup complete!"

cleanup-backups: ## Remove backups older than 30 days
	@echo "Cleaning up old backups..."
	find backups/ -type f -mtime +30 -delete 2>/dev/null || true
	@echo "Cleanup complete!"

# ============================================
# Cleanup
# ============================================

clean: ## Clean build artifacts and cache
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".benchmarks" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .benchmarks 2>/dev/null || true
	@echo "Clean complete!"

clean-all: clean ## Clean everything including Docker
	@echo "Cleaning Docker resources..."
	docker-compose down -v --remove-orphans 2>/dev/null || true
	docker system prune -f 2>/dev/null || true
	@echo "Full clean complete!"

# ============================================
# Monitoring
# ============================================

logs: ## Tail application logs
	@echo "Tailing application logs..."
	tail -f logs/app.log 2>/dev/null || echo "Log file not found. Run: tail -f /dev/null"

metrics: ## View application metrics
	@echo "Fetching metrics from /metrics endpoint..."
	curl -s http://localhost:8000/metrics 2>/dev/null || echo "API not running on port 8000"

health: ## Check application health
	@echo "Checking application health..."
	curl -s http://localhost:8000/health | python -m json.tool 2>/dev/null || echo "API not running on port 8000"

# ============================================
# Utilities
# ============================================

env-check: ## Check environment variables
	@echo "Checking required environment variables..."
	@for var in JWT_SECRET DATABASE_URL; do \
		if [ -z "$${!var}" ]; then \
			echo "MISSING: $$var"; \
		else \
			echo "OK: $$var"; \
		fi; \
	done

pre-commit: lint format test ## Run pre-commit checks

ci: pre-commit ## Run full CI pipeline
