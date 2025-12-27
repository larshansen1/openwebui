#!/bin/bash

set -e  # Exit on any error

echo "=================================================="
echo "Credential Rotation Script"
echo "=================================================="
echo "This script will rotate sensitive credentials:"
echo "  - POSTGRES_PASSWORD"
echo "  - WEBUI_SECRET_KEY"
echo "  - MCP_API_KEY"
echo ""
echo "⚠️  WARNING: This will:"
echo "  - Log out all users (WEBUI_SECRET_KEY change)"
echo "  - Restart all services"
echo "  - Take ~30 seconds"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Ensure we're in the correct directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file not found!${NC}"
    exit 1
fi

# Confirm with user
read -p "Do you want to continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "=================================================="
echo "Step 1: Generating New Credentials"
echo "=================================================="

# Generate new credentials
NEW_POSTGRES_PASSWORD=$(openssl rand -base64 32)
NEW_WEBUI_SECRET_KEY=$(openssl rand -hex 32)
NEW_MCP_API_KEY=$(openssl rand -base64 32)

echo -e "${GREEN}✓ Generated new POSTGRES_PASSWORD${NC}"
echo -e "${GREEN}✓ Generated new WEBUI_SECRET_KEY${NC}"
echo -e "${GREEN}✓ Generated new MCP_API_KEY${NC}"
echo ""

echo "=================================================="
echo "Step 2: Backing Up Current .env"
echo "=================================================="

# Backup current .env
cp .env .env.backup-$(date +%Y%m%d-%H%M%S)
echo -e "${GREEN}✓ Backed up .env${NC}"
echo ""

echo "=================================================="
echo "Step 3: Updating PostgreSQL Password in Database"
echo "=================================================="

# Check if PostgreSQL is running
if ! docker compose ps | grep -q "openwebui-postgres.*Up"; then
    echo -e "${RED}❌ Error: PostgreSQL container is not running${NC}"
    echo "Please start services first: docker compose up -d"
    exit 1
fi

# Update PostgreSQL password
echo "Updating PostgreSQL user password..."
docker compose exec -T postgres psql -U openwebui -d openwebui <<EOF
ALTER USER openwebui WITH PASSWORD '$NEW_POSTGRES_PASSWORD';
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ PostgreSQL password updated in database${NC}"
else
    echo -e "${RED}❌ Failed to update PostgreSQL password${NC}"
    echo "Restoring backup..."
    cp .env.backup-* .env 2>/dev/null || true
    exit 1
fi
echo ""

echo "=================================================="
echo "Step 4: Updating .env File"
echo "=================================================="

# Update .env file with new credentials
sed -i.bak "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$NEW_POSTGRES_PASSWORD|" .env
sed -i.bak "s|^WEBUI_SECRET_KEY=.*|WEBUI_SECRET_KEY=$NEW_WEBUI_SECRET_KEY|" .env
sed -i.bak "s|^MCP_API_KEY=.*|MCP_API_KEY=$NEW_MCP_API_KEY|" .env

# Remove sed backup file
rm -f .env.bak

echo -e "${GREEN}✓ Updated POSTGRES_PASSWORD in .env${NC}"
echo -e "${GREEN}✓ Updated WEBUI_SECRET_KEY in .env${NC}"
echo -e "${GREEN}✓ Updated MCP_API_KEY in .env${NC}"
echo ""

echo "=================================================="
echo "Step 5: Restarting Services"
echo "=================================================="

echo "Stopping services..."
docker compose down

echo ""
echo "Starting services with new credentials..."
docker compose up -d

echo ""
echo "Waiting for services to be healthy..."
sleep 15

echo ""
echo "=================================================="
echo "Step 6: Verifying Services"
echo "=================================================="

# Check if services are running
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
echo "=================================================="

if [ "$ALL_HEALTHY" = true ]; then
    echo -e "${GREEN}✅ Credential Rotation Successful!${NC}"
    echo "=================================================="
    echo ""
    echo "Summary:"
    echo "  ✓ PostgreSQL password rotated"
    echo "  ✓ WebUI secret key rotated (all users logged out)"
    echo "  ✓ MCP API key rotated"
    echo "  ✓ All services running"
    echo ""
    echo "Next steps:"
    echo "  1. Test login to Open WebUI"
    echo "  2. Verify database connectivity"
    echo "  3. Old .env backed up to: .env.backup-$(date +%Y%m%d)*"
    echo ""
else
    echo -e "${RED}⚠️  Credential Rotation Completed with Warnings${NC}"
    echo "=================================================="
    echo ""
    echo "Some services failed to start."
    echo "Check logs: docker compose logs"
    echo ""
    echo "To rollback:"
    echo "  1. docker compose down"
    echo "  2. cp .env.backup-* .env"
    echo "  3. ALTER USER openwebui WITH PASSWORD 'old-password';"
    echo "  4. docker compose up -d"
    echo ""
fi

echo "=================================================="
