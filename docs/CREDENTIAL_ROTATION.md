# Credential Rotation Guide

## When to Rotate Credentials

Rotate credentials immediately if:
- ✅ Credentials were exposed (committed to git, shared publicly, etc.)
- ✅ Suspected security breach
- ✅ Employee/team member leaves with access
- ✅ Periodic security maintenance (every 90 days recommended)

## Quick Rotation (Automated)

The easiest way to rotate credentials is using the automated script:

```bash
cd /home/admin/docker/openwebui

# Run the rotation script
./scripts/rotate-credentials.sh
```

### What the Script Does

1. **Generates new credentials** using `openssl rand`
2. **Backs up current .env** to `.env.backup-TIMESTAMP`
3. **Updates PostgreSQL password** in the database (ALTER USER)
4. **Updates .env file** with new credentials
5. **Restarts all services** with new credentials
6. **Verifies** all services are running

### Expected Output

```
==================================================
Credential Rotation Script
==================================================
This script will rotate sensitive credentials:
  - POSTGRES_PASSWORD
  - WEBUI_SECRET_KEY
  - MCP_API_KEY

⚠️  WARNING: This will:
  - Log out all users (WEBUI_SECRET_KEY change)
  - Restart all services
  - Take ~30 seconds

Do you want to continue? (yes/no): yes

==================================================
Step 1: Generating New Credentials
==================================================
✓ Generated new POSTGRES_PASSWORD
✓ Generated new WEBUI_SECRET_KEY
✓ Generated new MCP_API_KEY

==================================================
Step 2: Backing Up Current .env
==================================================
✓ Backed up .env

==================================================
Step 3: Updating PostgreSQL Password in Database
==================================================
Updating PostgreSQL user password...
ALTER ROLE
✓ PostgreSQL password updated in database

==================================================
Step 4: Updating .env File
==================================================
✓ Updated POSTGRES_PASSWORD in .env
✓ Updated WEBUI_SECRET_KEY in .env
✓ Updated MCP_API_KEY in .env

==================================================
Step 5: Restarting Services
==================================================
Stopping services...
[+] Running 5/5
 ✔ Container openwebui
 ✔ Container openwebui-postgres
 ...

Starting services with new credentials...
[+] Running 5/5
 ✔ Container openwebui-postgres  Started
 ...

==================================================
Step 6: Verifying Services
==================================================
✅ openwebui is running
✅ postgres is running
✅ qdrant is running
✅ ollama is running

==================================================
✅ Credential Rotation Successful!
==================================================

Summary:
  ✓ PostgreSQL password rotated
  ✓ WebUI secret key rotated (all users logged out)
  ✓ MCP API key rotated
  ✓ All services running

Next steps:
  1. Test login to Open WebUI
  2. Verify database connectivity
```

## Manual Rotation (Step by Step)

If you prefer manual control or the script fails:

### 1. Generate New Credentials

```bash
# Generate new passwords
NEW_POSTGRES_PASSWORD=$(openssl rand -base64 32)
NEW_WEBUI_SECRET_KEY=$(openssl rand -hex 32)
NEW_MCP_API_KEY=$(openssl rand -base64 32)

# Display them (copy for next steps)
echo "POSTGRES_PASSWORD=$NEW_POSTGRES_PASSWORD"
echo "WEBUI_SECRET_KEY=$NEW_WEBUI_SECRET_KEY"
echo "MCP_API_KEY=$NEW_MCP_API_KEY"
```

### 2. Update PostgreSQL Password in Database

```bash
# Connect to PostgreSQL and change password
docker compose exec postgres psql -U openwebui -d openwebui

# Inside PostgreSQL prompt:
ALTER USER openwebui WITH PASSWORD 'YOUR_NEW_POSTGRES_PASSWORD';
\q
```

### 3. Update .env File

```bash
# Backup first
cp .env .env.backup-$(date +%Y%m%d-%H%M%S)

# Edit .env file
nano .env

# Update these lines:
POSTGRES_PASSWORD=YOUR_NEW_POSTGRES_PASSWORD
WEBUI_SECRET_KEY=YOUR_NEW_WEBUI_SECRET_KEY
MCP_API_KEY=YOUR_NEW_MCP_API_KEY
```

### 4. Restart Services

```bash
docker compose down
docker compose up -d
```

### 5. Verify

```bash
# Check all services are running
docker compose ps

# Check logs for errors
docker compose logs openwebui | tail -20
docker compose logs postgres | tail -20
```

## Rollback Procedure

If rotation fails or causes issues:

### Option 1: Restore from Backup

```bash
# Stop services
docker compose down

# Restore old .env
cp .env.backup-YYYYMMDD-HHMMSS .env

# Update PostgreSQL password back to old value
docker compose up -d postgres
docker compose exec postgres psql -U openwebui -d openwebui
# Inside psql:
ALTER USER openwebui WITH PASSWORD 'OLD_PASSWORD_FROM_BACKUP';
\q

# Restart all services
docker compose down
docker compose up -d
```

### Option 2: Fix Forward

If you can't find the old password:

```bash
# Reset PostgreSQL completely (⚠️ DANGEROUS - only if you have database backup)
docker compose down
docker volume rm openwebui_postgres_data  # ⚠️ DELETES ALL DATA
docker compose up -d
```

**DON'T DO THIS unless you have a recent database backup!**

## Best Practices

1. **Test after rotation** - Verify you can log in and access data
2. **Keep backups** - The script creates `.env.backup-*` files automatically
3. **Rotate on schedule** - Set a reminder for every 90 days
4. **Use strong passwords** - Always use `openssl rand` for generation
5. **Document who has access** - Track who knows production credentials
6. **Rotate after exposure** - If credentials leaked, rotate immediately

## Impact of Each Credential

### POSTGRES_PASSWORD
- **Impact**: Medium
- **What breaks if wrong**: Database connection fails, app won't start
- **User impact**: Complete outage
- **Recovery**: Rollback or reset password

### WEBUI_SECRET_KEY
- **Impact**: High (user sessions)
- **What breaks if wrong**: Nothing breaks, but all users logged out
- **User impact**: Everyone must re-login
- **Recovery**: No recovery needed, users just login again

### MCP_API_KEY
- **Impact**: Low
- **What breaks if wrong**: MCP server features won't work
- **User impact**: Web search and MCP features disabled
- **Recovery**: Rotate again or rollback

## Troubleshooting

### PostgreSQL won't accept new password

```bash
# Check if PostgreSQL is running
docker compose ps postgres

# Check PostgreSQL logs
docker compose logs postgres | tail -50

# Try connecting with old password
docker compose exec postgres psql -U openwebui -d openwebui

# If that works, the database still has old password
# Manually run: ALTER USER openwebui WITH PASSWORD 'new-password';
```

### Services won't start after rotation

```bash
# Check logs for all services
docker compose logs --tail=50

# Common issues:
# - DATABASE_URL syntax error in docker-compose.yml
# - Special characters in password need escaping
# - .env file has extra spaces or quotes

# Verify .env file
cat .env | grep -E "POSTGRES_PASSWORD|WEBUI_SECRET_KEY|MCP_API_KEY"
```

### Can't login after WEBUI_SECRET_KEY rotation

This is **expected behavior**! The new secret key invalidates all existing sessions.

Solution: Just log in again with your username/password.

### How to rotate on both dev and production

```bash
# On production:
./scripts/rotate-credentials.sh

# On dev:
./scripts/rotate-credentials.sh

# Note: Dev and prod will have DIFFERENT credentials (good!)
# They don't need to match
```

## Security Checklist After Exposure

If credentials were exposed in git or publicly:

- [ ] Rotate all three credentials immediately
- [ ] Check git history for credential commits
- [ ] If in git, consider entire git history compromised
- [ ] Notify team members
- [ ] Review access logs for suspicious activity
- [ ] Consider rotating API keys (OPENAI_API_KEY, BRAVE_API_KEY)
- [ ] Update any documentation that referenced old credentials
- [ ] Force all users to reset passwords (if user data exposed)

## See Also

- [scripts/rotate-credentials.sh](../scripts/rotate-credentials.sh) - Automated rotation script
- [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) - Environment variable guide
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide
