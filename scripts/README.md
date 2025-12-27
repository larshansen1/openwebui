# Deployment Scripts

These scripts automate the deployment process for your Open WebUI production environment.

## Scripts

### `backup.sh`
Creates a backup of your current production state before deployment.

**What it backs up:**
- PostgreSQL database (SQL dump)
- Configuration files (docker-compose.yml, .env, Dockerfiles)
- Custom scripts
- MCP config templates

**What it doesn't backup:**
- Data volumes (postgres_data/, openwebui_data/, qdrant_data/, ollama_data/)
- These are preserved in place and never modified by deployments

**Usage:**
```bash
./backup.sh
```

**Output:**
Creates a timestamped directory: `backups/backup-YYYYMMDD-HHMMSS/`

**Auto-cleanup:**
Automatically keeps the last 10 backups and removes older ones.

---

### `deploy.sh`
Safely deploys changes to production without affecting your data.

**What it does:**
1. Checks for required files (.env, docker-compose.yml)
2. Pulls latest changes from git
3. Detects if Dockerfiles changed (to determine if rebuild is needed)
4. Stops containers gracefully (using `docker-compose down`)
5. Rebuilds images (with or without cache based on changes)
6. Starts services (`docker-compose up -d`)
7. Waits for services to be healthy
8. Verifies all critical services are running

**What it preserves:**
- All data volumes remain untouched
- Your .env file is used (not overwritten)
- Only containers are recreated, data persists

**Usage:**
```bash
./deploy.sh
```

**Exit codes:**
- `0` - Success (all services healthy)
- `1` - Failure (missing files, service failed to start, etc.)

---

## Safety Features

### Data Protection
- **Never deletes volumes**: Data directories are never touched by deployment scripts
- **Volume persistence**: Docker volumes persist across container restarts
- **Database safety**: PostgreSQL data remains intact even during container recreation

### Backup Strategy
- **Automatic backups**: Every deployment is preceded by a backup
- **Timestamped backups**: Easy to identify when backups were created
- **Retention policy**: Last 10 backups are kept automatically
- **Manual backups**: You can run `backup.sh` anytime, not just during deployments

### Rollback Capability
If something goes wrong, you can rollback:
```bash
# Restore config from backup
cp backups/backup-YYYYMMDD-HHMMSS/docker-compose.yml .
cp backups/backup-YYYYMMDD-HHMMSS/env.backup .env

# Restart services
./deploy.sh
```

## Usage Examples

### Standard Deployment
```bash
# Backup first (done automatically in GitHub Actions)
./backup.sh

# Deploy
./deploy.sh
```

### Manual Backup
```bash
# Create a backup without deploying
./backup.sh
```

### Emergency Rollback
```bash
# Stop services
docker-compose down

# Restore from last backup
LAST_BACKUP=$(ls -1dt backups/backup-* | head -n1)
cp $LAST_BACKUP/docker-compose.yml .
cp $LAST_BACKUP/env.backup .env
cp $LAST_BACKUP/Dockerfile.* .

# Restart
./deploy.sh
```

### Deploy with Fresh Rebuild
```bash
# Force rebuild all images (ignoring cache)
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Integration with GitHub Actions

These scripts are designed to work seamlessly with GitHub Actions:

**Workflow file:** `.github/workflows/deploy-production.yml`

**Trigger:** Automatically runs when you push to `main` branch

**Runner:** Executes on your production laptop (self-hosted runner)

**Process:**
1. GitHub detects push to main
2. Workflow starts on production laptop
3. Runs `backup.sh` to create backup
4. Runs `deploy.sh` to deploy changes
5. Verifies services are healthy
6. Reports success/failure

## Customization

### Add Custom Pre-Deployment Checks
Edit `deploy.sh` and add before the `docker-compose down` line:

```bash
# Custom checks
if ! curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "Warning: Service not responding before deployment"
fi
```

### Add Post-Deployment Tasks
Edit `deploy.sh` and add after services start:

```bash
# Warm up cache
docker-compose exec openwebui curl -f http://localhost:8080/health || true
```

### Change Backup Retention
Edit `backup.sh` and modify:

```bash
# Keep last 20 instead of 10
ls -1dt backups/backup-* | tail -n +21 | xargs rm -rf
```

### Add Notification
Edit `deploy.sh` to send notifications:

```bash
# Send email on success
if [ "$ALL_HEALTHY" = true ]; then
    echo "Deployment successful!" | mail -s "Deployment Success" you@example.com
fi
```

## Troubleshooting

### Scripts Won't Execute
```bash
# Make sure they're executable
chmod +x scripts/*.sh
```

### Backup Fails
```bash
# Check disk space
df -h

# Check if PostgreSQL is running
docker-compose ps postgres

# Test database connection
docker-compose exec postgres psql -U openwebui -c "SELECT 1;"
```

### Deploy Fails
```bash
# Check detailed logs
docker-compose logs --tail=100

# Verify Docker is running
systemctl status docker

# Check for port conflicts
sudo lsof -i :3000,5432,6333,11434

# Ensure .env file exists
ls -la .env
```

### Services Don't Start
```bash
# Check individual service logs
docker-compose logs openwebui
docker-compose logs postgres
docker-compose logs qdrant
docker-compose logs ollama

# Restart specific service
docker-compose restart openwebui

# Full restart
docker-compose down && docker-compose up -d
```

## Best Practices

1. **Always backup before manual changes**: Run `./backup.sh` before making manual changes
2. **Test scripts in dev first**: Test deployment scripts in your dev environment before using in production
3. **Monitor first deployment**: Watch the logs during your first deployment to ensure everything works
4. **Keep manual backups**: Archive important backups outside of the auto-cleanup system
5. **Review changes**: Use `git diff` to review what's being deployed before pushing

## See Also

- [DEPLOYMENT.md](../docs/DEPLOYMENT.md) - Complete deployment guide
- [QUICK_START.md](../docs/QUICK_START.md) - Quick start guide
- [docker-compose.yml](../docker-compose.yml) - Service definitions
