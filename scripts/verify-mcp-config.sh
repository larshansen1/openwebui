#!/bin/bash
# Verify MCP server is accessible with the configured API key
# Run this after deployment to ensure tools are working

set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "Verifying MCP server configuration..."

# Test MCP server authentication
echo "Testing MCP API key..."
RESPONSE=$(docker exec openwebui curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer ${MCP_API_KEY}" \
    http://mcp-server:8000/time/openapi.json 2>/dev/null || echo "FAILED")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" != "200" ]; then
    echo "ERROR: MCP server authentication failed (HTTP $HTTP_CODE)"
    echo "This means the MCP_API_KEY in .env doesn't match what the MCP server expects"
    exit 1
fi

echo "✓ MCP server authentication successful"

# Test from openwebui container
echo "Testing from Open WebUI container..."
RESPONSE=$(docker exec openwebui curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer ${MCP_API_KEY}" \
    http://mcp-server:8000/brave-search/openapi.json 2>/dev/null || echo "FAILED")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" != "200" ]; then
    echo "ERROR: Cannot reach MCP server from OpenWebUI container"
    exit 1
fi

echo "✓ MCP server accessible from OpenWebUI"
echo "✓ All checks passed!"
echo ""
echo "If tools still show 'Invalid API key' in the UI, run:"
echo "  ./scripts/reset-tool-config.sh"
echo "  docker compose restart openwebui"
