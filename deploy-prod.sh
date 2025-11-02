#!/bin/bash
# Production deployment script

set -e  # Exit on error

echo "=========================================="
echo "Production Deployment - Crypto Trading Agent"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites met${NC}"
echo ""

# Load environment
if [ ! -f .env.production ]; then
    echo -e "${RED}❌ .env.production file not found${NC}"
    echo "Please create .env.production from .env.production template"
    exit 1
fi

# Warning for production
echo -e "${YELLOW}⚠️  WARNING: You are deploying to PRODUCTION${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
if [[ ! $REPLY =~ ^yes$ ]]; then
    echo "Deployment cancelled"
    exit 1
fi

# Build images
echo ""
echo "Building Docker images..."
docker-compose build --no-cache

# Run database migrations
echo ""
echo "Running database migrations..."
docker-compose run --rm trading_agent python -m alembic upgrade head

# Start services
echo ""
echo "Starting services..."
docker-compose up -d

# Wait for health checks
echo ""
echo "Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "Checking service health..."

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U trading_user > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL is healthy${NC}"
else
    echo -e "${RED}❌ PostgreSQL health check failed${NC}"
    exit 1
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is healthy${NC}"
else
    echo -e "${RED}❌ Redis health check failed${NC}"
    exit 1
fi

# Display status
echo ""
echo "=========================================="
echo -e "${GREEN}✅ Deployment Successful!${NC}"
echo "=========================================="
echo ""
echo "Services:"
echo "  • Trading Agent: http://localhost:8000"
echo "  • Grafana: http://localhost:3000 (admin/admin)"
echo "  • Prometheus: http://localhost:9091"
echo ""
echo "Commands:"
echo "  • View logs: docker-compose logs -f trading_agent"
echo "  • Stop all: docker-compose down"
echo "  • Restart: docker-compose restart trading_agent"
echo ""
echo "Monitor the agent at http://localhost:3000"
echo "=========================================="
