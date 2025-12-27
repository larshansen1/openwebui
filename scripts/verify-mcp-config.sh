#!/bin/bash
# Verify MCP server tools are actually working through Open WebUI
# Run this after deployment to ensure tools are working

set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "Verifying MCP server configuration..."

# Test MCP server authentication (direct)
echo "Testing MCP server direct access..."
RESPONSE=$(docker exec openwebui curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer ${MCP_API_KEY}" \
    http://mcp-server:8000/time/openapi.json 2>/dev/null || echo "FAILED")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" != "200" ]; then
    echo "ERROR: MCP server authentication failed (HTTP $HTTP_CODE)"
    echo "This means the MCP_API_KEY in .env doesn't match what the MCP server expects"
    exit 1
fi

echo "✓ MCP server direct access successful"

# Check TOOL_SERVER_CONNECTIONS has the correct API key
echo "Checking TOOL_SERVER_CONNECTIONS environment variable..."
TOOL_KEY=$(docker exec openwebui sh -c 'echo "$TOOL_SERVER_CONNECTIONS"' | grep -o '"key": "[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$TOOL_KEY" ]; then
    echo "ERROR: No API key found in TOOL_SERVER_CONNECTIONS"
    exit 1
fi

if [ "$TOOL_KEY" != "$MCP_API_KEY" ]; then
    echo "ERROR: TOOL_SERVER_CONNECTIONS has wrong API key"
    echo "  Expected: ${MCP_API_KEY}"
    echo "  Found: ${TOOL_KEY}"
    exit 1
fi

echo "✓ TOOL_SERVER_CONNECTIONS has correct API key"

# Wait for OpenWebUI to be fully ready and register tools
echo "Waiting for OpenWebUI to register tools in database..."
MAX_WAIT=60
WAITED=0
TOOL_COUNT=0

while [ $WAITED -lt $MAX_WAIT ]; do
    TOOL_COUNT=$(docker exec openwebui-postgres psql -U openwebui -d openwebui -t -c \
        "SELECT COUNT(*) FROM config WHERE data::text LIKE '%tool_server%';" 2>/dev/null | xargs || echo "0")

    if [ "$TOOL_COUNT" != "0" ]; then
        break
    fi

    echo "  Waiting for tools to register... (${WAITED}s/${MAX_WAIT}s)"
    sleep 5
    WAITED=$((WAITED + 5))
done

if [ "$TOOL_COUNT" = "0" ]; then
    echo "ERROR: Tools not registered in database after ${MAX_WAIT}s"
    echo "Check OpenWebUI logs: docker logs openwebui --tail 50"
    exit 1
fi

echo "✓ Tool servers registered in database"

# The definitive test: Check if database has the CURRENT API key
echo "Verifying stored tool configuration matches current API key..."
STORED_CONFIG=$(docker exec openwebui-postgres psql -U openwebui -d openwebui -t -c \
    "SELECT data FROM config WHERE data::text LIKE '%tool_server%';" 2>/dev/null)

if [ -z "$STORED_CONFIG" ]; then
    echo "ERROR: Cannot retrieve stored configuration from database"
    exit 1
fi

# Extract API key from stored config (handle both formats: "key":"value" and "key": "value")
STORED_KEY=$(echo "$STORED_CONFIG" | grep -o '"key"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)".*/\1/')

if [ -z "$STORED_KEY" ]; then
    echo "ERROR: Cannot extract API key from stored configuration"
    echo "Stored config: $STORED_CONFIG"
    exit 1
fi

if [ "$STORED_KEY" != "$MCP_API_KEY" ]; then
    echo "ERROR: Stored tool configuration has WRONG API key!"
    echo "  Current .env: ${MCP_API_KEY}"
    echo "  Stored in DB: ${STORED_KEY}"
    echo ""
    echo "This is why tools show 'Invalid API key' error."
    echo "Database config needs to be reset."
    exit 1
fi

echo "✓ Stored tool configuration matches current API key"
echo "✓ All checks passed - MCP tools should work correctly!"
