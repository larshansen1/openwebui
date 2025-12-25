#!/bin/bash
# Generate Strong Credentials for Open WebUI Setup
# This script creates cryptographically secure random keys for all services

set -e

echo "🔐 Credential Generator for Open WebUI"
echo "======================================="
echo ""
echo "⚠️  WARNING: Save these credentials securely!"
echo "   They will be needed in your .env file"
echo ""

# Function to generate a strong key
generate_key() {
    openssl rand -base64 32 | tr -d '\n'
}

# Function to generate a hex key
generate_hex_key() {
    openssl rand -hex 32 | tr -d '\n'
}

echo "Generating credentials..."
echo ""

# PostgreSQL Password
POSTGRES_PASSWORD=$(generate_key)
echo "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}"

# WebUI Secret Key (hex for JWT)
WEBUI_SECRET_KEY=$(generate_hex_key)
echo "WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}"

# Qdrant API Key
QDRANT_API_KEY=$(generate_key)
echo "QDRANT_API_KEY=${QDRANT_API_KEY}"

# MCP Server API Key
MCP_API_KEY=$(generate_key)
echo "MCP_API_KEY=${MCP_API_KEY}"

echo ""
echo "======================================="
echo "✅ Credentials generated successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Copy the credentials above"
echo "   2. Update your .env file with these values"
echo "   3. Keep OPENAI_API_KEY and BRAVE_API_KEY from your existing .env"
echo "   4. Restart services: docker compose up -d"
echo ""
echo "🔒 Security notes:"
echo "   - These credentials are cryptographically secure (32-byte keys)"
echo "   - Store them safely (password manager, encrypted vault)"
echo "   - Never commit .env to version control"
echo "   - Rotate credentials periodically (every 90 days recommended)"
echo ""
