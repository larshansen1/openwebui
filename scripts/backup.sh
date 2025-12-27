#!/bin/bash

set -e  # Exit on any error

echo "=================================================="
echo "Starting Pre-Deployment Backup"
echo "=================================================="
echo "Timestamp: $(date)"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Ensure we're in the correct directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Create backup directory with timestamp
BACKUP_DIR="backups/backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo -e "${YELLOW}📁 Backup directory: $BACKUP_DIR${NC}"
echo ""

# Backup PostgreSQL database
echo -e "${GREEN}💾 Backing up PostgreSQL database...${NC}"
if docker-compose ps | grep -q "openwebui-postgres.*Up"; then
    # Source environment variables
    if [ -f .env ]; then
        source .env
    fi

    docker-compose exec -T postgres pg_dump -U openwebui openwebui > "$BACKUP_DIR/postgres_backup.sql" 2>/dev/null || {
        echo -e "${YELLOW}⚠️  Warning: Could not backup PostgreSQL (container may not be running)${NC}"
    }

    if [ -f "$BACKUP_DIR/postgres_backup.sql" ]; then
        echo -e "${GREEN}✅ PostgreSQL backup created: $(du -h "$BACKUP_DIR/postgres_backup.sql" | cut -f1)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  PostgreSQL container not running - skipping database backup${NC}"
fi
echo ""

# Backup configuration files
echo -e "${GREEN}📋 Backing up configuration files...${NC}"
cp docker-compose.yml "$BACKUP_DIR/" 2>/dev/null || true
cp .env "$BACKUP_DIR/env.backup" 2>/dev/null || true

# Backup Dockerfiles
cp Dockerfile.* "$BACKUP_DIR/" 2>/dev/null || true

# Backup MCP config template
mkdir -p "$BACKUP_DIR/mcp_config"
cp mcp_config/config.template.json "$BACKUP_DIR/mcp_config/" 2>/dev/null || true

# Backup custom scripts
cp *.sh "$BACKUP_DIR/" 2>/dev/null || true

echo -e "${GREEN}✅ Configuration files backed up${NC}"
echo ""

# Create a backup manifest
echo -e "${GREEN}📝 Creating backup manifest...${NC}"
cat > "$BACKUP_DIR/MANIFEST.txt" <<EOF
Backup Information
==================
Date: $(date)
Hostname: $(hostname)
Project Directory: $PROJECT_DIR

Files Backed Up:
- docker-compose.yml
- .env (as env.backup)
- Dockerfiles
- MCP config template
- Custom scripts
- PostgreSQL database dump (if available)

Data Volumes (not backed up - preserved in place):
- postgres_data/
- openwebui_data/
- qdrant_data/
- ollama_data/

To restore this backup:
1. Copy configuration files back to project directory
2. Restore PostgreSQL: docker-compose exec -T postgres psql -U openwebui openwebui < postgres_backup.sql
3. Restart services: docker-compose up -d

Note: Data volumes are preserved in place and not included in backups.
EOF

echo -e "${GREEN}✅ Manifest created${NC}"
echo ""

# Show backup summary
echo -e "${GREEN}=================================================="
echo "✅ Backup Complete!"
echo "=================================================="
echo "Backup location: $BACKUP_DIR"
echo "Backup size: $(du -sh "$BACKUP_DIR" | cut -f1)"
echo ""
echo "Contents:"
ls -lh "$BACKUP_DIR"
echo -e "==================================================${NC}"
echo ""

# Clean up old backups (keep last 10)
echo -e "${YELLOW}🧹 Cleaning up old backups (keeping last 10)...${NC}"
BACKUP_COUNT=$(ls -1d backups/backup-* 2>/dev/null | wc -l || echo "0")
if [ "$BACKUP_COUNT" -gt 10 ]; then
    ls -1dt backups/backup-* | tail -n +11 | xargs rm -rf
    echo -e "${GREEN}✅ Cleaned up $((BACKUP_COUNT - 10)) old backups${NC}"
else
    echo "No cleanup needed (${BACKUP_COUNT} backups total)"
fi
echo ""
