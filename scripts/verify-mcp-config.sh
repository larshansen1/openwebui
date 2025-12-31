#!/bin/bash
# Verify MCP server tools are actually working
# Tests actual functionality instead of database state

set -e

# Load environment variables safely
if [ -f .env ]; then
    set -a  # automatically export all variables
    source .env
    set +a  # stop automatically exporting
fi

echo "Verifying MCP server configuration..."

# 1. Check MCP_API_KEY is set
if [ -z "$MCP_API_KEY" ]; then
    echo "ERROR: MCP_API_KEY not set in .env"
    exit 1
fi

echo "✓ MCP_API_KEY is set"

# 2. Test MCP server direct access
echo "Testing MCP server authentication..."
RESPONSE=$(docker exec openwebui curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer ${MCP_API_KEY}" \
    http://mcp-server:8000/time/openapi.json 2>/dev/null || echo "FAILED")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" != "200" ]; then
    echo "ERROR: MCP server authentication failed (HTTP $HTTP_CODE)"
    echo "The MCP_API_KEY in .env doesn't match what the MCP server expects"
    exit 1
fi

echo "✓ MCP server authentication successful"

# 3. Check TOOL_SERVER_CONNECTIONS env var is set in openwebui container
echo "Checking TOOL_SERVER_CONNECTIONS in OpenWebUI container..."
TOOL_CONN=$(docker exec openwebui sh -c 'echo "$TOOL_SERVER_CONNECTIONS"' 2>/dev/null)

if [ -z "$TOOL_CONN" ]; then
    echo "ERROR: TOOL_SERVER_CONNECTIONS not set in openwebui container"
    echo "Check docker-compose.yml environment section"
    exit 1
fi

echo "✓ TOOL_SERVER_CONNECTIONS is set"

# 4. Verify the API key in TOOL_SERVER_CONNECTIONS matches MCP_API_KEY
TOOL_KEY=$(echo "$TOOL_CONN" | grep -o '"key"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)".*/\1/')

if [ -z "$TOOL_KEY" ]; then
    echo "ERROR: Cannot extract API key from TOOL_SERVER_CONNECTIONS"
    exit 1
fi

if [ "$TOOL_KEY" != "$MCP_API_KEY" ]; then
    echo "ERROR: API key mismatch!"
    echo "  MCP_API_KEY in .env: ${MCP_API_KEY}"
    echo "  Key in TOOL_SERVER_CONNECTIONS: ${TOOL_KEY}"
    exit 1
fi

echo "✓ API keys match"

# 5. Wait for OpenWebUI to be fully ready
echo "Waiting for OpenWebUI to be ready..."
MAX_WAIT=30
WAITED=0

while [ $WAITED -lt $MAX_WAIT ]; do
    HTTP_CODE=$(docker exec openwebui curl -s -w "%{http_code}" -o /dev/null http://localhost:8080/api/version 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" = "200" ]; then
        break
    fi

    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "ERROR: OpenWebUI not responding after ${MAX_WAIT}s"
    exit 1
fi

echo "✓ OpenWebUI is ready"

# 6. Actually test a tool by calling the MCP endpoint with the configured key
echo "Testing actual tool functionality..."
TEST_RESULT=$(docker exec openwebui curl -s -X POST \
    -H "Authorization: Bearer ${MCP_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"timezone":"UTC"}' \
    http://mcp-server:8000/time/get_current_time 2>/dev/null || echo "FAILED")

if echo "$TEST_RESULT" | grep -q "Invalid API key\|403\|401"; then
    echo "ERROR: Tool call failed with authentication error"
    echo "Response: $TEST_RESULT"
    exit 1
fi

if echo "$TEST_RESULT" | grep -q "error"; then
    echo "ERROR: Tool call failed"
    echo "Response: $TEST_RESULT"
    exit 1
fi

echo "✓ Tool functionality verified"

# 7. Verify obsidian-mcp is healthy and responding
echo "Verifying Obsidian MCP server..."
OBSIDIAN_HEALTH=$(docker exec openwebui curl -s \
    http://obsidian-mcp:8000/health 2>/dev/null || echo "FAILED")

if ! echo "$OBSIDIAN_HEALTH" | grep -q "healthy"; then
    echo "ERROR: Obsidian MCP health check failed"
    echo "Response: $OBSIDIAN_HEALTH"
    exit 1
fi

echo "✓ Obsidian MCP is healthy"

# 8. Verify obsidian-mcp mode matches USE_PROXY_MODE setting
echo "Verifying Obsidian MCP endpoint mode..."
OBSIDIAN_PATHS=$(docker exec openwebui curl -s \
    http://obsidian-mcp:8000/openapi.json 2>/dev/null | \
    python3 -c "import sys,json; print(','.join(json.load(sys.stdin).get('paths',{}).keys()))" 2>/dev/null || echo "FAILED")

# Check if in proxy mode (has /mcp/execute) or direct mode (has /tools/)
if echo "$OBSIDIAN_PATHS" | grep -q "/mcp/execute"; then
    echo "✓ Obsidian MCP in proxy mode (3 proxy tools)"
elif echo "$OBSIDIAN_PATHS" | grep -q "/tools/"; then
    echo "✓ Obsidian MCP in direct mode (23+ direct tools)"
else
    echo "ERROR: Obsidian MCP has unexpected endpoint configuration"
    echo "Endpoints: $OBSIDIAN_PATHS"
    exit 1
fi

# 9. Test obsidian-mcp authentication
OBSIDIAN_AUTH=$(docker exec openwebui curl -s -X GET \
    -H "Authorization: Bearer ${MCP_API_KEY}" \
    http://obsidian-mcp:8000/vault/stats 2>/dev/null || echo "FAILED")

if echo "$OBSIDIAN_AUTH" | grep -q "Invalid API key\|403\|401\|Forbidden"; then
    echo "ERROR: Obsidian MCP authentication failed"
    echo "Response: $OBSIDIAN_AUTH"
    exit 1
fi

echo "✓ Obsidian MCP authentication successful"
echo ""
echo "✅ All checks passed - MCP tools are configured correctly!"
