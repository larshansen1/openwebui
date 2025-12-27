#!/bin/bash

# Validates that all required environment variables are set

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=================================================="
echo "Validating Environment Variables"
echo "=================================================="
echo ""

# Ensure we're in the correct directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file not found!${NC}"
    echo "Please create .env from .env.template:"
    echo "  cp .env.template .env"
    echo "  # Then edit .env and fill in your values"
    exit 1
fi

# Source the .env file
set -a
source .env
set +a

# List of required variables (must not be empty)
REQUIRED_VARS=(
    "POSTGRES_PASSWORD"
    "WEBUI_SECRET_KEY"
    "RAG_EMBEDDING_MODEL"
    "MCP_API_KEY"
)

# List of optional but recommended variables
RECOMMENDED_VARS=(
    "OPENAI_API_KEY"
    "QDRANT_API_KEY"
    "BRAVE_API_KEY"
)

MISSING_REQUIRED=()
MISSING_RECOMMENDED=()

# Check required variables
echo -e "${GREEN}Checking required variables:${NC}"
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "  ${RED}✗ $var${NC} - NOT SET"
        MISSING_REQUIRED+=("$var")
    else
        echo -e "  ${GREEN}✓ $var${NC} - Set"
    fi
done

echo ""
echo -e "${YELLOW}Checking recommended variables:${NC}"
for var in "${RECOMMENDED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "  ${YELLOW}⚠ $var${NC} - Not set (optional)"
        MISSING_RECOMMENDED+=("$var")
    else
        echo -e "  ${GREEN}✓ $var${NC} - Set"
    fi
done

echo ""
echo "=================================================="

# Report results
if [ ${#MISSING_REQUIRED[@]} -gt 0 ]; then
    echo -e "${RED}❌ Validation Failed!${NC}"
    echo ""
    echo "Missing required variables:"
    for var in "${MISSING_REQUIRED[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please update your .env file with these variables."
    echo "See .env.template for documentation and examples."
    exit 1
fi

if [ ${#MISSING_RECOMMENDED[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Warning: Some recommended variables are not set${NC}"
    echo ""
    echo "Missing recommended variables:"
    for var in "${MISSING_RECOMMENDED[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Your deployment will work, but some features may be disabled."
fi

echo -e "${GREEN}✅ Environment validation passed!${NC}"
echo "=================================================="
