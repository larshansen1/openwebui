#!/bin/sh
set -e

echo "🔒 Obsidian MCP Server Startup"
echo "=============================="

# Validate required environment variables
if [ -z "$MCP_API_KEY" ]; then
    echo "❌ ERROR: MCP_API_KEY environment variable is required"
    exit 1
fi

if [ ${#MCP_API_KEY} -lt 16 ]; then
    echo "❌ ERROR: MCP_API_KEY must be at least 16 characters for security"
    exit 1
fi

if [ -z "$OBSIDIAN_VAULT_PATH" ]; then
    echo "❌ ERROR: OBSIDIAN_VAULT_PATH environment variable is required"
    exit 1
fi

echo "✅ Environment variables validated"

# Check if vault directory exists
if [ ! -d "$OBSIDIAN_VAULT_PATH" ]; then
    echo "❌ ERROR: Vault directory does not exist: $OBSIDIAN_VAULT_PATH"
    echo ""
    echo "Available paths:"
    ls -la / 2>/dev/null || echo "Cannot list root directory"
    exit 1
fi

echo "✅ Vault directory exists: $OBSIDIAN_VAULT_PATH"

# Check if vault contains at least one .md file
MD_COUNT=$(find "$OBSIDIAN_VAULT_PATH" -type f -name "*.md" 2>/dev/null | wc -l)
if [ "$MD_COUNT" -eq 0 ]; then
    echo "❌ ERROR: Vault is empty (no .md files found): $OBSIDIAN_VAULT_PATH"
    echo ""
    echo "Contents of vault directory:"
    ls -la "$OBSIDIAN_VAULT_PATH" 2>/dev/null || echo "Cannot list vault directory"
    exit 1
fi

echo "✅ Vault validated successfully"
echo "📝 Found $MD_COUNT markdown file(s)"
echo ""

echo "🚀 Starting Obsidian MCP Server..."
exec "$@"
