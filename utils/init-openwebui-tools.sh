#!/bin/bash
set -e

# Configuration
OPENWEBUI_URL="${OPENWEBUI_URL:-http://localhost:3000}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@localhost}"
ADMIN_PASSWORD="${ADMIN_PASSWORD}"
ADMIN_NAME="${ADMIN_NAME:-Admin}"
CONFIG_FILE="/config/openwebui-tools-config.json"

echo "🚀 Open WebUI Tools Initialization Script"
echo "=========================================="

# Wait for Open WebUI to be ready
echo "⏳ Waiting for Open WebUI to be ready..."
max_attempts=60
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s -f "${OPENWEBUI_URL}/health" > /dev/null 2>&1; then
        echo "✅ Open WebUI is ready!"
        break
    fi
    attempt=$((attempt + 1))
    echo "   Attempt $attempt/$max_attempts..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Open WebUI did not become ready in time"
    exit 1
fi

# Check if admin password is set
if [ -z "$ADMIN_PASSWORD" ]; then
    echo "⚠️  ADMIN_PASSWORD not set. Skipping automatic configuration."
    echo "   Please configure tools manually or set ADMIN_PASSWORD environment variable."
    exit 0
fi

# Try to sign in (user might already exist)
echo "🔐 Attempting to authenticate..."
TOKEN=$(curl -s -X POST "${OPENWEBUI_URL}/api/v1/auths/signin" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" \
    | jq -r '.token // empty' 2>/dev/null || echo "")

# If signin failed, try to create admin user
if [ -z "$TOKEN" ]; then
    echo "📝 Admin user doesn't exist. Creating admin user..."
    TOKEN=$(curl -s -X POST "${OPENWEBUI_URL}/api/v1/auths/signup" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\",\"name\":\"${ADMIN_NAME}\"}" \
        | jq -r '.token // empty' 2>/dev/null || echo "")
fi

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to authenticate or create admin user"
    exit 1
fi

echo "✅ Authenticated successfully!"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚠️  Configuration file not found: $CONFIG_FILE"
    exit 0
fi

# Read and process tools configuration
echo "📋 Reading tools configuration..."
TOOLS_COUNT=$(jq '.tools | length' "$CONFIG_FILE")
echo "   Found $TOOLS_COUNT tools to configure"

# Substitute environment variables in the config
TEMP_CONFIG=$(mktemp)
envsubst < "$CONFIG_FILE" > "$TEMP_CONFIG"

# Process each tool
for i in $(seq 0 $((TOOLS_COUNT - 1))); do
    TOOL=$(jq ".tools[$i]" "$TEMP_CONFIG")
    TOOL_ID=$(echo "$TOOL" | jq -r '.id')
    TOOL_NAME=$(echo "$TOOL" | jq -r '.name')
    TOOL_URL=$(echo "$TOOL" | jq -r '.url')

    echo ""
    echo "🔧 Configuring tool: $TOOL_NAME ($TOOL_ID)"
    echo "   URL: $TOOL_URL"

    # Prepare the tool payload
    # Note: The actual API structure might differ - adjust based on Open WebUI's API
    PAYLOAD=$(echo "$TOOL" | jq '{
        id: .id,
        name: .name,
        description: .description,
        url: .url,
        headers: .headers,
        enabled: .enabled
    }')

    # Try to create the tool
    RESPONSE=$(curl -s -X POST "${OPENWEBUI_URL}/api/v1/tools/create" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" 2>&1 || echo "{}")

    # Check if successful
    if echo "$RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
        echo "   ✅ Tool created successfully!"
    elif echo "$RESPONSE" | grep -q "already exists" 2>/dev/null; then
        echo "   ℹ️  Tool already exists, skipping..."
    else
        echo "   ⚠️  API endpoint might not exist yet. Manual configuration required."
        echo "   Response: $RESPONSE"
    fi
done

rm -f "$TEMP_CONFIG"

echo ""
echo "=========================================="
echo "✅ Tool initialization complete!"
echo ""
echo "📌 If automatic configuration didn't work, please configure manually:"
echo "   1. Go to Settings → Tools in Open WebUI"
echo "   2. Add the following endpoints:"
for i in $(seq 0 $((TOOLS_COUNT - 1))); do
    TOOL_NAME=$(jq -r ".tools[$i].name" "$CONFIG_FILE")
    TOOL_URL=$(jq -r ".tools[$i].url" "$CONFIG_FILE")
    echo "      - $TOOL_NAME: $TOOL_URL"
done
echo ""
