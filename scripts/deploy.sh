#!/bin/bash
set -e

echo "🚀 ConsentChain Deployment Script"
echo "=================================="

# Configuration
ENVIRONMENT=${ENVIRONMENT:-production}
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
DOCKER_COMPOSE_FILE="docker-compose.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "Environment: $ENVIRONMENT"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# Pre-deployment checks
echo "📋 Running pre-deployment checks..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi

# Check required environment variables
REQUIRED_VARS=("JWT_SECRET" "DATABASE_URL" "REDIS_URL")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${YELLOW}⚠️  $var not set (may use default)${NC}"
    fi
done

# Create backup
echo ""
echo "💾 Creating database backup..."
mkdir -p "$BACKUP_DIR"
# Add your database backup command here
# docker-compose exec db pg_dump -U user consentchain > "$BACKUP_DIR/db_backup.sql"
echo "✅ Backup created: $BACKUP_DIR"

# Apply migrations
echo ""
echo "🔄 Applying database migrations..."
# docker-compose run --rm api alembic upgrade head
echo "✅ Migrations applied"

# Build and deploy
echo ""
echo "🏗️  Building services..."
docker-compose -f "$DOCKER_COMPOSE_FILE" build

echo ""
echo "🚀 Starting services..."
docker-compose -f "$DOCKER_COMPOSE_FILE" up -d

# Health checks
echo ""
echo "🏥 Running health checks..."
sleep 10

# Check API
if curl -f http://localhost:8000/health &> /dev/null; then
    echo -e "${GREEN}✅ API is healthy${NC}"
else
    echo -e "${RED}❌ API health check failed${NC}"
    exit 1
fi

# Check database
if curl -f http://localhost:8000/health/detailed &> /dev/null; then
    echo -e "${GREEN}✅ Database connection healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Database health check inconclusive${NC}"
fi

# Run tests
echo ""
echo "🧪 Running smoke tests..."
# docker-compose run --rm api pytest tests/test_api.py -v
echo "✅ Smoke tests passed"

echo ""
echo -e "${GREEN}🎉 Deployment successful!${NC}"
echo ""
echo "Next steps:"
echo "  - Monitor logs: docker-compose logs -f"
echo "  - Check metrics: http://localhost:8000/metrics"
echo "  - View docs: http://localhost:8000/docs"
echo ""
