#!/bin/bash
# Test tool integration between Open WebUI and AI models

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Testing Open WebUI Tool Integration${NC}"
echo "======================================"

# Load environment
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# 1. Test OpenAPI spec is fetchable
echo -e "\n${YELLOW}1. Testing OpenAPI spec accessibility...${NC}"
SPEC=$(docker compose exec obsidian-mcp curl -s http://localhost:8000/openapi.json)

if echo "$SPEC" | grep -q '"openapi"'; then
    echo -e "${GREEN}✓ OpenAPI spec is valid${NC}"
    TOOL_COUNT=$(echo "$SPEC" | grep -o '"operationId"' | wc -l)
    echo "  Found $TOOL_COUNT tool endpoints"
else
    echo -e "${RED}✗ OpenAPI spec is invalid${NC}"
    exit 1
fi

# 2. Test tool authentication
echo -e "\n${YELLOW}2. Testing tool authentication...${NC}"
RESPONSE=$(docker compose exec obsidian-mcp curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer ${MCP_API_KEY}" \
    http://localhost:8000/tools/list_tags)

HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Tool authentication working${NC}"
else
    echo -e "${RED}✗ Tool authentication failed (HTTP $HTTP_CODE)${NC}"
    exit 1
fi

# 3. Check Open WebUI can access the spec
echo -e "\n${YELLOW}3. Testing Open WebUI access to MCP server...${NC}"
OPENWEBUI_SPEC=$(docker compose exec openwebui curl -s \
    http://obsidian-mcp:8000/openapi.json)

if echo "$OPENWEBUI_SPEC" | grep -q '"openapi"'; then
    echo -e "${GREEN}✓ Open WebUI can access OpenAPI spec${NC}"
else
    echo -e "${RED}✗ Open WebUI cannot access MCP server${NC}"
    exit 1
fi

# 4. Test actual tool execution from Open WebUI container
echo -e "\n${YELLOW}4. Testing tool execution from Open WebUI...${NC}"
TEST_RESPONSE=$(docker compose exec openwebui curl -s -X GET \
    -H "Authorization: Bearer ${MCP_API_KEY}" \
    http://obsidian-mcp:8000/tools/list_tags)

if echo "$TEST_RESPONSE" | grep -q '"success".*true'; then
    echo -e "${GREEN}✓ Tool execution successful${NC}"
    TAG_COUNT=$(echo "$TEST_RESPONSE" | grep -o '"count":[0-9]*' | head -1 | grep -o '[0-9]*')
    echo "  Found $TAG_COUNT unique tags in vault"
else
    echo -e "${RED}✗ Tool execution failed${NC}"
    echo "Response: $TEST_RESPONSE"
    exit 1
fi

# 5. Check TOOL_SERVER_CONNECTIONS in Open WebUI
echo -e "\n${YELLOW}5. Checking TOOL_SERVER_CONNECTIONS configuration...${NC}"
TOOL_CONNECTIONS=$(docker compose exec openwebui sh -c 'echo "$TOOL_SERVER_CONNECTIONS"')

if echo "$TOOL_CONNECTIONS" | grep -q 'obsidian-vault'; then
    echo -e "${GREEN}✓ Obsidian Vault configured in TOOL_SERVER_CONNECTIONS${NC}"

    # Check if the API key matches
    CONFIGURED_KEY=$(echo "$TOOL_CONNECTIONS" | grep -o '"key"[[:space:]]*:[[:space:]]*"[^"]*"' | grep -A1 'obsidian' | tail -1 | sed 's/.*"\([^"]*\)".*/\1/')

    if [ "$CONFIGURED_KEY" = "$MCP_API_KEY" ]; then
        echo -e "${GREEN}✓ API key matches${NC}"
    else
        echo -e "${RED}✗ API key mismatch${NC}"
        echo "  Expected: ${MCP_API_KEY}"
        echo "  Got: ${CONFIGURED_KEY}"
    fi
else
    echo -e "${RED}✗ Obsidian Vault not found in TOOL_SERVER_CONNECTIONS${NC}"
    exit 1
fi

# Summary
echo -e "\n${GREEN}=====================================${NC}"
echo -e "${GREEN}All MCP server tests passed!${NC}"
echo -e "${GREEN}=====================================${NC}"

echo -e "\n${YELLOW}If AI models still can't see tools:${NC}"
echo "1. The issue is in Open WebUI's AI provider integration"
echo "2. Check Open WebUI logs for tool-related errors"
echo "3. Try different models/providers (Claude, GPT-4, etc.)"
echo "4. Check Open WebUI version - tool support improved in recent versions"
echo "5. Verify the AI provider supports function calling"
