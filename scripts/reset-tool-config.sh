#!/bin/bash
# Reset MCP tool configuration by recreating containers
# This forces containers to reload environment variables from .env

set -e

echo "Resetting MCP tool server configuration..."
echo ""
echo "⚠️  IMPORTANT: This will recreate the OpenWebUI container to reload environment variables."
echo "   Active connections will be dropped. This is necessary because 'docker compose restart'"
echo "   does NOT reload environment variables from .env file."
echo ""

# Recreate only the necessary containers (not postgres which has data)
echo "Recreating openwebui and mcp-server containers..."
docker compose up -d --force-recreate mcp-server openwebui

echo ""
echo "✓ Containers recreated with latest environment variables"
echo "  Waiting for services to be ready..."

# Wait for OpenWebUI to be ready
MAX_WAIT=60
WAITED=0

while [ $WAITED -lt $MAX_WAIT ]; do
    if docker exec openwebui curl -s -f http://localhost:8080/api/version > /dev/null 2>&1; then
        echo "✓ OpenWebUI is ready"
        echo ""
        echo "✅ Reset complete! MCP tools should now use the updated API key from .env"
        exit 0
    fi

    sleep 2
    WAITED=$((WAITED + 2))
done

echo "⚠ OpenWebUI may not be fully ready yet. Check logs: docker logs openwebui"
exit 0
