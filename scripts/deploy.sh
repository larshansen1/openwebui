#!/bin/bash

set -e  # Exit on any error

echo "=================================================="
echo "Starting Production Deployment"
echo "=================================================="
echo "Timestamp: $(date)"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Ensure we're in the correct directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo -e "${YELLOW}📍 Working directory: $PROJECT_DIR${NC}"
echo ""

# Check if required files exist
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file not found!${NC}"
    echo "Please ensure your production .env file exists before deploying."
    exit 1
fi

if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Error: docker-compose.yml not found!${NC}"
    exit 1
fi

# Pull latest changes (if running from git)
echo -e "${GREEN}📥 Pulling latest changes from git...${NC}"
git pull origin main || echo "Note: git pull failed or not in a git repo"
echo ""

# Check which services need to be rebuilt
echo -e "${GREEN}🔍 Checking for Dockerfile changes...${NC}"
REBUILD_NEEDED=false

# Check if Dockerfiles have changed in recent commits
if git diff HEAD~1 HEAD --name-only | grep -q "Dockerfile"; then
    REBUILD_NEEDED=true
    echo "Dockerfile changes detected - will rebuild images"
else
    echo "No Dockerfile changes - using existing images"
fi
echo ""

# Stop containers gracefully (but don't remove volumes!)
echo -e "${YELLOW}🛑 Stopping containers gracefully...${NC}"
docker compose down --remove-orphans
echo ""

# Rebuild images if needed
if [ "$REBUILD_NEEDED" = true ]; then
    echo -e "${GREEN}🔨 Rebuilding Docker images...${NC}"
    docker compose build --no-cache
    echo ""
else
    echo -e "${GREEN}🔨 Building/pulling images (using cache)...${NC}"
    docker compose build
    echo ""
fi

# Start services
echo -e "${GREEN}🚀 Starting services...${NC}"
docker compose up -d
echo ""

# Wait for services to be healthy
echo -e "${YELLOW}⏳ Waiting for services to be healthy...${NC}"
echo "This may take a minute..."
sleep 15

# Check service health
echo ""
echo -e "${GREEN}📊 Service Status:${NC}"
docker compose ps
echo ""

# Check if critical services are running
CRITICAL_SERVICES=("openwebui" "postgres" "qdrant" "ollama")
ALL_HEALTHY=true

for service in "${CRITICAL_SERVICES[@]}"; do
    if docker compose ps | grep "$service" | grep -q "Up"; then
        echo -e "${GREEN}✅ $service is running${NC}"
    else
        echo -e "${RED}❌ $service is NOT running${NC}"
        ALL_HEALTHY=false
    fi
done

echo ""
if [ "$ALL_HEALTHY" = true ]; then
    echo -e "${GREEN}=================================================="
    echo "✅ Deployment Successful!"
    echo "=================================================="
    echo "All services are running."
    echo "Your production data has been preserved."
    echo "Timestamp: $(date)"
    echo -e "==================================================${NC}"
else
    echo -e "${RED}=================================================="
    echo "⚠️  Deployment completed with warnings"
    echo "=================================================="
    echo "Some services may not be running correctly."
    echo "Check logs with: docker compose logs"
    echo -e "==================================================${NC}"
    exit 1
fi
