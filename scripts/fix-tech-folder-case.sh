#!/bin/bash
# Quick fix for Tech/ → tech/ case issue

set -e

echo "🔧 Fixing Tech/ → tech/ case mismatch..."

# Check if this is running in container or on host
if [ "$1" = "container" ]; then
    VAULT_PATH="/vault"
else
    # Load vault path from .env
    if [ -f .env ]; then
        source .env
    fi
    VAULT_PATH="${OBSIDIAN_VAULT_PATH:-./obsidian-mcp/test-vault}"
fi

echo "Vault path: $VAULT_PATH"

# Check if Tech/ exists
if [ -d "$VAULT_PATH/Tech" ]; then
    echo "✓ Found: $VAULT_PATH/Tech"

    # Rename using intermediate temp name (required for case-insensitive filesystems)
    echo "  Step 1: Tech/ → tech_temp/"
    mv "$VAULT_PATH/Tech" "$VAULT_PATH/tech_temp"

    echo "  Step 2: tech_temp/ → tech/"
    mv "$VAULT_PATH/tech_temp" "$VAULT_PATH/tech"

    echo "✅ Renamed: Tech/ → tech/"

    # List contents
    if [ -d "$VAULT_PATH/tech" ]; then
        echo ""
        echo "Contents of tech/:"
        ls -la "$VAULT_PATH/tech/"
    fi
elif [ -d "$VAULT_PATH/tech" ]; then
    echo "✓ Already lowercase: tech/"
    echo "  No action needed."
else
    echo "❌ Neither Tech/ nor tech/ found in vault"
    echo "  Available directories:"
    ls -la "$VAULT_PATH/"
fi

echo ""
echo "Done!"
