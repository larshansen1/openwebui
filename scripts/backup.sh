#!/bin/bash
#
# Backup Script with Encryption
# ==============================
# Creates encrypted backups of sensitive files (.env, database)
# using GPG symmetric encryption with AES256.
#
# Default passphrase: "openwebui-backup"
# Custom passphrase: Set BACKUP_ENCRYPTION_KEY environment variable
#
# Usage:
#   ./backup.sh                                    # Use default passphrase
#   BACKUP_ENCRYPTION_KEY="my-secret" ./backup.sh  # Use custom passphrase
#
# Requirements: gpg (gnupg) must be installed
#   macOS: brew install gnupg
#   Ubuntu/Debian: apt-get install gnupg
#

set -e  # Exit on any error

echo "=================================================="
echo "Starting Pre-Deployment Backup"
echo "=================================================="
echo "Timestamp: $(date)"
if [ -n "$BACKUP_ENCRYPTION_KEY" ]; then
    echo "Using custom encryption key"
else
    echo "Using default encryption key (set BACKUP_ENCRYPTION_KEY for custom)"
fi
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
if docker compose ps | grep -q "openwebui-postgres.*Up"; then
    # Source environment variables
    if [ -f .env ]; then
        source .env
    fi

    docker compose exec -T postgres pg_dump -U openwebui openwebui > "$BACKUP_DIR/postgres_backup.sql" 2>/dev/null || {
        echo -e "${YELLOW}⚠️  Warning: Could not backup PostgreSQL (container may not be running)${NC}"
    }

    if [ -f "$BACKUP_DIR/postgres_backup.sql" ]; then
        DB_SIZE=$(du -h "$BACKUP_DIR/postgres_backup.sql" | cut -f1)
        echo -e "${GREEN}✅ PostgreSQL backup created: $DB_SIZE${NC}"

        # Encrypt database backup (may contain sensitive data)
        if command -v gpg &> /dev/null; then
            echo -e "${YELLOW}🔐 Encrypting database backup...${NC}"
            gpg --symmetric --cipher-algo AES256 --batch --yes \
                --passphrase-file <(echo "${BACKUP_ENCRYPTION_KEY:-openwebui-backup}") \
                --output "$BACKUP_DIR/postgres_backup.sql.gpg" \
                "$BACKUP_DIR/postgres_backup.sql" 2>/dev/null && {
                # Remove unencrypted version after successful encryption
                rm -f "$BACKUP_DIR/postgres_backup.sql"
                echo -e "${GREEN}✅ Database backup encrypted${NC}"
            } || {
                echo -e "${YELLOW}⚠️  Failed to encrypt database backup - keeping unencrypted${NC}"
            }
        else
            echo -e "${YELLOW}⚠️  Database backup stored unencrypted (install GPG for encryption)${NC}"
        fi
    fi
else
    echo -e "${YELLOW}⚠️  PostgreSQL container not running - skipping database backup${NC}"
fi
echo ""

# Backup configuration files
echo -e "${GREEN}📋 Backing up configuration files...${NC}"
cp docker-compose.yml "$BACKUP_DIR/" 2>/dev/null || true

# Encrypt sensitive .env file with GPG
if [ -f .env ]; then
    echo -e "${YELLOW}🔐 Encrypting .env file with GPG...${NC}"
    if command -v gpg &> /dev/null; then
        # Use symmetric encryption (password-based)
        gpg --symmetric --cipher-algo AES256 --batch --yes \
            --passphrase-file <(echo "${BACKUP_ENCRYPTION_KEY:-openwebui-backup}") \
            --output "$BACKUP_DIR/env.backup.gpg" .env 2>/dev/null && \
            echo -e "${GREEN}✅ .env encrypted successfully${NC}" || \
            echo -e "${RED}❌ Failed to encrypt .env - GPG may not be available${NC}"
    else
        echo -e "${YELLOW}⚠️  GPG not installed - backing up .env unencrypted (NOT RECOMMENDED)${NC}"
        cp .env "$BACKUP_DIR/env.backup" 2>/dev/null || true
    fi
else
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
fi

# Backup Dockerfiles (not sensitive)
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
- docker-compose.yml (unencrypted)
- env.backup.gpg (ENCRYPTED - contains all credentials)
- postgres_backup.sql.gpg (ENCRYPTED - database dump)
- Dockerfiles (unencrypted)
- MCP config template (unencrypted)
- Custom scripts (unencrypted)

Encryption:
- Algorithm: AES256 (GPG symmetric encryption)
- Default passphrase: "openwebui-backup"
- To use custom passphrase: Set BACKUP_ENCRYPTION_KEY environment variable

Data Volumes (not backed up - preserved in place):
- postgres_data/
- openwebui_data/
- qdrant_data/
- ollama_data/

To restore this backup:

1. Decrypt .env file:
   gpg --decrypt --batch --passphrase "openwebui-backup" \
       env.backup.gpg > .env

2. Decrypt database backup:
   gpg --decrypt --batch --passphrase "openwebui-backup" \
       postgres_backup.sql.gpg > postgres_backup.sql

3. Restore PostgreSQL:
   docker compose exec -T postgres psql -U openwebui openwebui < postgres_backup.sql

4. Copy other configuration files back to project directory

5. Restart services:
   docker compose up -d

Security Notes:
- Encrypted files (.gpg) are safe to store in cloud backup services
- Keep encryption passphrase secure and separate from backups
- For production, use a strong custom passphrase via BACKUP_ENCRYPTION_KEY
- Data volumes are preserved in place and not included in backups

Note: If GPG was not available during backup, files may be unencrypted.
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
