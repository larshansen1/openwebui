#!/bin/bash
# Open WebUI Version Check Script
# Displays version information for Open WebUI container and software

set -e

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Open WebUI Version Information${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# Check if container is running
if ! docker ps --filter "name=openwebui" --format "{{.Names}}" | grep -q "^openwebui$"; then
    echo -e "${RED}Error: openwebui container is not running${NC}"
    exit 1
fi

echo -e "${GREEN}Software Version:${NC}"
# Get version from API
VERSION=$(curl -s http://127.0.0.1:3000/api/version 2>/dev/null | grep -o '"version":"[^"]*' | cut -d'"' -f4)
if [ -n "$VERSION" ]; then
    echo "  Open WebUI: v$VERSION"
else
    echo "  Unable to fetch version from API"
fi

echo ""
echo -e "${GREEN}Container Information:${NC}"
# Get container details
docker inspect openwebui --format='  Base Image: {{.Config.Image}}
  Container Created: {{.Created}}
  Status: {{.State.Status}}' 2>/dev/null

echo ""
echo -e "${GREEN}Image Details:${NC}"
# Get image labels and creation date
LABELS=$(docker inspect openwebui --format='{{json .Config.Labels}}' 2>/dev/null)
IMAGE_CREATED=$(echo "$LABELS" | grep -o '"org.opencontainers.image.created":"[^"]*' | cut -d'"' -f4)
GIT_REVISION=$(echo "$LABELS" | grep -o '"org.opencontainers.image.revision":"[^"]*' | cut -d'"' -f4)
IMAGE_VERSION=$(echo "$LABELS" | grep -o '"org.opencontainers.image.version":"[^"]*' | cut -d'"' -f4)

echo "  Built: $IMAGE_CREATED"
echo "  Git Commit: $GIT_REVISION"
echo "  Branch: $IMAGE_VERSION"

# Get architecture
ARCH=$(docker inspect ghcr.io/open-webui/open-webui:main --format='{{.Architecture}}' 2>/dev/null)
echo "  Architecture: $ARCH"

echo ""
echo -e "${GREEN}Related Components:${NC}"
# Check other running containers
docker ps --filter "name=openwebui-" --format "  {{.Names}}: {{.Image}}" | sed 's/openwebui-/  /' | sort

echo ""
echo -e "${YELLOW}Compatibility Notes:${NC}"
# Check for compatibility warnings in logs
if docker logs openwebui 2>&1 | grep -q "incompatible"; then
    echo -e "  ${YELLOW}⚠ Compatibility warnings found in logs:${NC}"
    docker logs openwebui 2>&1 | grep -i "incompatible" | tail -3 | sed 's/^/    /'
else
    echo "  ✓ No compatibility warnings detected"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
