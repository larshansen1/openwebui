#!/bin/bash
# Fix case sensitivity issues in Obsidian vault for Syncthing
# This script renames directories to lowercase to match Linux conventions

set -e

# Try to auto-detect vault path
if [ -z "$1" ]; then
    if [ -d "/vault" ]; then
        VAULT_PATH="/vault"
    elif [ -d "../syncthing/vault" ]; then
        VAULT_PATH="../syncthing/vault"
    elif [ -d "~/docker/syncthing/vault" ]; then
        VAULT_PATH="~/docker/syncthing/vault"
    else
        echo "❌ Could not auto-detect vault path"
        echo "Usage: $0 <path-to-vault>"
        echo "Example: $0 ~/docker/syncthing/vault"
        exit 1
    fi
else
    VAULT_PATH="$1"
fi

# Expand tilde
VAULT_PATH="${VAULT_PATH/#\~/$HOME}"

# Check if path exists
if [ ! -d "$VAULT_PATH" ]; then
    echo "❌ Vault path does not exist: $VAULT_PATH"
    echo ""
    echo "Please provide the correct path to your vault."
    echo "Usage: $0 <path-to-vault>"
    exit 1
fi

echo "🔍 Checking for case sensitivity issues in vault..."
echo "Vault path: $VAULT_PATH"
echo ""

# Find all directories (excluding .obsidian)
echo "Current directory structure:"
find "$VAULT_PATH" -type d -not -path "*/.obsidian*" | sort

echo ""
echo "📋 Case normalization plan:"
echo "=============================="

# Strategy: Rename using a temp name first to avoid conflicts on case-insensitive filesystems
# Example: Tech/ → tech_temp → tech/

# Array to store rename operations
declare -a RENAMES

# Find directories with capital letters (excluding .obsidian)
while IFS= read -r dir; do
    basename=$(basename "$dir")
    lowercase=$(echo "$basename" | tr '[:upper:]' '[:lower:]')

    # Skip if already lowercase or is .obsidian
    if [ "$basename" != "$lowercase" ] && [ "$basename" != ".obsidian" ]; then
        parent=$(dirname "$dir")
        echo "  $basename → $lowercase (in $parent)"
        RENAMES+=("$parent/$basename|$lowercase")
    fi
done < <(find "$VAULT_PATH" -type d -not -path "*/.obsidian*" | sort -r)

if [ ${#RENAMES[@]} -eq 0 ]; then
    echo "✅ No case issues found - all directories are already lowercase!"
    exit 0
fi

echo ""
read -p "Proceed with renaming? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "🔧 Applying renames..."

for rename in "${RENAMES[@]}"; do
    parent=$(echo "$rename" | cut -d'|' -f1 | xargs dirname)
    old_name=$(echo "$rename" | cut -d'|' -f1 | xargs basename)
    new_name=$(echo "$rename" | cut -d'|' -f2)

    old_path="$parent/$old_name"
    temp_path="$parent/${new_name}_temp_rename"
    new_path="$parent/$new_name"

    echo "  Renaming: $old_path"

    # Step 1: Rename to temp name
    if [ -d "$old_path" ]; then
        mv "$old_path" "$temp_path"
        echo "    → $temp_path (temp)"
    fi

    # Step 2: Rename to final lowercase name
    if [ -d "$temp_path" ]; then
        mv "$temp_path" "$new_path"
        echo "    → $new_path (final)"
    fi
done

echo ""
echo "✅ Case normalization complete!"
echo ""
echo "New directory structure:"
find "$VAULT_PATH" -type d -not -path "*/.obsidian*" | sort
