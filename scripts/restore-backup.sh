#!/bin/bash
#
# Restore Encrypted Backup
# =========================
# Decrypts and restores backups created by backup.sh
#
# Usage:
#   ./restore-backup.sh <backup-directory>
#   BACKUP_ENCRYPTION_KEY="my-secret" ./restore-backup.sh <backup-directory>
#
# Example:
#   ./restore-backup.sh backups/backup-20250128-143000
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No backup directory specified${NC}"
    echo "Usage: $0 <backup-directory>"
    echo "Example: $0 backups/backup-20250128-143000"
    exit 1
fi

BACKUP_DIR="$1"

if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${RED}Error: Backup directory not found: $BACKUP_DIR${NC}"
    exit 1
fi

echo "=================================================="
echo "Restoring Backup from Encrypted Files"
echo "=================================================="
echo "Backup: $BACKUP_DIR"
echo "Timestamp: $(date)"
echo ""

# Check for GPG
if ! command -v gpg &> /dev/null; then
    echo -e "${RED}Error: GPG not installed${NC}"
    echo "Install GPG first:"
    echo "  macOS: brew install gnupg"
    echo "  Ubuntu/Debian: apt-get install gnupg"
    exit 1
fi

# Get encryption passphrase
PASSPHRASE="${BACKUP_ENCRYPTION_KEY:-openwebui-backup}"

# Decrypt .env file
if [ -f "$BACKUP_DIR/env.backup.gpg" ]; then
    echo -e "${YELLOW}🔓 Decrypting .env file...${NC}"
    gpg --decrypt --batch --yes --passphrase "$PASSPHRASE" \
        --output .env "$BACKUP_DIR/env.backup.gpg" && \
        echo -e "${GREEN}✅ .env decrypted successfully${NC}" || {
        echo -e "${RED}❌ Failed to decrypt .env - wrong passphrase?${NC}"
        exit 1
    }
elif [ -f "$BACKUP_DIR/env.backup" ]; then
    echo -e "${YELLOW}📋 Copying unencrypted .env file...${NC}"
    cp "$BACKUP_DIR/env.backup" .env
    echo -e "${GREEN}✅ .env restored${NC}"
else
    echo -e "${YELLOW}⚠️  No .env backup found${NC}"
fi

# Decrypt database backup
if [ -f "$BACKUP_DIR/postgres_backup.sql.gpg" ]; then
    echo -e "${YELLOW}🔓 Decrypting database backup...${NC}"
    gpg --decrypt --batch --yes --passphrase "$PASSPHRASE" \
        --output "$BACKUP_DIR/postgres_backup.sql" \
        "$BACKUP_DIR/postgres_backup.sql.gpg" && \
        echo -e "${GREEN}✅ Database backup decrypted${NC}" || {
        echo -e "${RED}❌ Failed to decrypt database backup - wrong passphrase?${NC}"
        exit 1
    }
fi

# Restore PostgreSQL database
if [ -f "$BACKUP_DIR/postgres_backup.sql" ]; then
    echo -e "${YELLOW}💾 Restoring PostgreSQL database...${NC}"

    # Check if container is running
    if docker compose ps | grep -q "openwebui-postgres.*Up"; then
        docker compose exec -T postgres psql -U openwebui openwebui < "$BACKUP_DIR/postgres_backup.sql" && \
            echo -e "${GREEN}✅ Database restored successfully${NC}" || {
            echo -e "${RED}❌ Failed to restore database${NC}"
            exit 1
        }

        # Clean up decrypted SQL file for security
        rm -f "$BACKUP_DIR/postgres_backup.sql"
        echo -e "${YELLOW}🧹 Cleaned up decrypted SQL file${NC}"
    else
        echo -e "${YELLOW}⚠️  PostgreSQL container not running${NC}"
        echo "Start containers first: docker compose up -d"
        echo "Decrypted SQL file saved at: $BACKUP_DIR/postgres_backup.sql"
    fi
else
    echo -e "${YELLOW}⚠️  No database backup found${NC}"
fi

# Restore other configuration files
echo -e "${YELLOW}📋 Restoring configuration files...${NC}"
if [ -f "$BACKUP_DIR/docker-compose.yml" ]; then
    cp "$BACKUP_DIR/docker-compose.yml" . && \
        echo -e "${GREEN}✅ docker-compose.yml restored${NC}"
fi

echo ""
echo -e "${GREEN}=================================================="
echo "✅ Backup Restore Complete!"
echo "=================================================="
echo "Next steps:"
echo "1. Review restored .env file"
echo "2. Restart services: docker compose down && docker compose up -d"
echo -e "==================================================${NC}"
