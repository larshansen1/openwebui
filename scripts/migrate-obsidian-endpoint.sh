#!/bin/bash
# Migration script: Update OpenWebUI tool server configuration
# Changes obsidian-mcp endpoint to mcp-server/obsidian endpoint
#
# Usage: ./scripts/migrate-obsidian-endpoint.sh

set -e

echo "🔄 Migrating Obsidian tool endpoint configuration..."
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if postgres is running
if ! docker ps | grep -q openwebui-postgres; then
    echo -e "${RED}❌ PostgreSQL container is not running${NC}"
    exit 1
fi

# Get current configuration
echo "📊 Current configuration:"
CURRENT=$(docker compose exec -T postgres psql -U openwebui -d openwebui -At -c "
    SELECT data->'tool_server'->'connections'->3->>'url' 
    FROM config 
    WHERE id = 1;
")

echo "  Current endpoint: $CURRENT"

# Check if already migrated
if echo "$CURRENT" | grep -q "mcp-server:8000/obsidian"; then
    echo -e "${GREEN}✅ Already migrated to new endpoint${NC}"
    echo "  No changes needed."
    exit 0
fi

# Perform migration
echo ""
echo -e "${YELLOW}⚙️  Updating database configuration...${NC}"

docker compose exec -T postgres psql -U openwebui -d openwebui <<'EOF'
UPDATE config SET data = jsonb_set(
  data::jsonb,
  '{tool_server,connections,3}',
  '{
    "url": "http://mcp-server:8000/obsidian",
    "path": "openapi.json",
    "type": "openapi",
    "auth_type": "bearer",
    "key": "rgjdfj5rtggFDsdeGhdeRRtggC_fFG",
    "config": {"enable": true},
    "spec_type": "url",
    "spec": "",
    "info": {
      "id": "obsidian",
      "name": "Obsidian Vault",
      "description": "Read, write, search, and manage Obsidian vault notes"
    }
  }'::jsonb
)::json 
WHERE id = 1;
EOF

# Verify migration
echo ""
echo "🔍 Verifying migration..."
NEW=$(docker compose exec -T postgres psql -U openwebui -d openwebui -At -c "
    SELECT data->'tool_server'->'connections'->3->>'url' 
    FROM config 
    WHERE id = 1;
")

if echo "$NEW" | grep -q "mcp-server:8000/obsidian"; then
    echo -e "${GREEN}✅ Migration successful!${NC}"
    echo "  New endpoint: $NEW"
    echo ""
    echo -e "${YELLOW}⚠️  Note: OpenWebUI must be restarted to pick up the change${NC}"
    echo "  Run: docker compose restart openwebui"
else
    echo -e "${RED}❌ Migration failed!${NC}"
    echo "  Endpoint: $NEW"
    exit 1
fi
