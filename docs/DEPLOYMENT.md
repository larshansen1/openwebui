# Production Deployment Pipeline

This guide explains how to set up automated deployments from your development environment to production using GitHub Actions.

## Overview

The deployment pipeline:
1. **Backs up** your current production state (database + config)
2. **Pulls** latest changes from the main branch
3. **Rebuilds** containers only if Dockerfiles changed
4. **Restarts** services gracefully
5. **Preserves** all your data (never touches data volumes)
6. **Verifies** all services are running

## Architecture

```
Dev Environment (Local)  →  GitHub (main branch)  →  Production (Local Laptop)
     ↓                              ↓                          ↓
  Make changes            Push to trigger workflow    Self-hosted runner
  Test locally            OR manual trigger           executes deployment
```

## Setup Instructions

### Step 1: Set Up GitHub Actions Self-Hosted Runner on Production

Since your production is on a local laptop, you need to install a GitHub Actions runner on it.

1. **On your production laptop**, navigate to your GitHub repository settings:
   ```
   https://github.com/<your-username>/<your-repo>/settings/actions/runners
   ```

2. Click **"New self-hosted runner"** and select **Linux**

3. Follow the installation commands provided by GitHub (similar to):
   ```bash
   # Download the runner
   mkdir -p ~/actions-runner && cd ~/actions-runner
   curl -o actions-runner-linux-x64-2.X.X.tar.gz -L https://github.com/actions/runner/releases/download/vX.X.X/actions-runner-linux-x64-2.X.X.tar.gz
   tar xzf ./actions-runner-linux-x64-2.X.X.tar.gz

   # Configure the runner
   ./config.sh --url https://github.com/<your-username>/<your-repo> --token <YOUR_TOKEN>
   ```

4. **Install as a service** so it runs automatically:
   ```bash
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```

5. Verify the runner is online in your GitHub repository settings

### Step 2: Configure Production Environment

1. **Ensure production directory is a git clone**:
   ```bash
   cd /path/to/production/openwebui
   git remote -v  # Should show your GitHub repo
   ```

2. **Make sure .env file exists** with your production secrets (already done ✓)

3. **Create backups directory**:
   ```bash
   mkdir -p backups
   ```

### Step 3: Test the Deployment Scripts Manually

Before using the automated pipeline, test the scripts:

1. **Make scripts executable**:
   ```bash
   chmod +x scripts/backup.sh scripts/deploy.sh
   ```

2. **Test backup script**:
   ```bash
   ./scripts/backup.sh
   # Check that backups/ directory was created with your data
   ```

3. **Test deployment script**:
   ```bash
   ./scripts/deploy.sh
   # Verify all services restart successfully
   ```

## Usage

### Automated Deployment (Recommended)

1. **On your dev machine**, make changes and test them locally

2. **Commit and push to main**:
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```

3. **GitHub Actions automatically**:
   - Triggers the workflow
   - Runs on your production laptop (self-hosted runner)
   - Backs up current state
   - Deploys changes
   - Verifies services are healthy

4. **Monitor the deployment**:
   - Go to your GitHub repository → Actions tab
   - Watch the deployment progress in real-time

### Manual Deployment

You can also trigger deployments manually:

1. Go to **Actions** tab in your GitHub repository
2. Select **"Deploy to Production"** workflow
3. Click **"Run workflow"**
4. Select branch (usually `main`)
5. Click **"Run workflow"** button

### Direct Deployment (Emergency)

If GitHub is down or you need to deploy immediately:

```bash
# On production laptop
cd /path/to/production/openwebui
./scripts/backup.sh   # Always backup first!
git pull origin main
./scripts/deploy.sh
```

## Safety Features

### Data Protection

The deployment scripts **NEVER** delete or modify these directories:
- `postgres_data/` - Your PostgreSQL database
- `openwebui_data/` - Open WebUI application data
- `qdrant_data/` - Vector database
- `ollama_data/` - Ollama models and data

These volumes persist across deployments.

### Automatic Backups

Before every deployment:
- PostgreSQL database is dumped to SQL file
- Configuration files are backed up
- Backup is timestamped and stored in `backups/`
- Old backups are auto-cleaned (keeps last 10)

### Rollback Procedure

If a deployment fails or causes issues:

1. **Stop services**:
   ```bash
   docker-compose down
   ```

2. **Restore configuration**:
   ```bash
   # Find your backup
   ls -lt backups/

   # Restore from backup
   cp backups/backup-YYYYMMDD-HHMMSS/docker-compose.yml .
   cp backups/backup-YYYYMMDD-HHMMSS/env.backup .env
   cp backups/backup-YYYYMMDD-HHMMSS/Dockerfile.* .
   ```

3. **Optionally restore database**:
   ```bash
   docker-compose up -d postgres
   docker-compose exec -T postgres psql -U openwebui openwebui < backups/backup-YYYYMMDD-HHMMSS/postgres_backup.sql
   ```

4. **Restart services**:
   ```bash
   ./scripts/deploy.sh
   ```

## Workflow Customization

### Deploy to Different Branch

Edit `.github/workflows/deploy-production.yml`:

```yaml
on:
  push:
    branches:
      - production  # Change from 'main' to 'production'
```

### Add Deployment Notifications

You can add Slack/Discord notifications by adding steps to the workflow:

```yaml
- name: Send Slack notification
  if: success()
  run: |
    curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"✅ Production deployment successful!"}' \
    ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Add Health Checks

Modify `scripts/deploy.sh` to add more thorough health checks:

```bash
# Wait for Open WebUI to respond
for i in {1..30}; do
  if curl -f http://localhost:3000 >/dev/null 2>&1; then
    echo "✅ Open WebUI is responding"
    break
  fi
  sleep 2
done
```

## Troubleshooting

### Runner Not Picking Up Jobs

- Check runner status: `sudo ./svc.sh status` on production laptop
- Verify runner is online in GitHub settings
- Check runner logs: `~/actions-runner/_diag/Runner_*.log`

### Deployment Fails

- Check GitHub Actions logs for error messages
- Manually run `./scripts/deploy.sh` on production to see detailed output
- Verify Docker daemon is running: `systemctl status docker`
- Check disk space: `df -h`

### Services Not Starting

- Check logs: `docker-compose logs <service-name>`
- Verify .env file has all required variables
- Check if ports are already in use: `sudo lsof -i :3000,5432,6333,11434`

### Database Connection Issues

- Verify PostgreSQL is healthy: `docker-compose ps postgres`
- Check database logs: `docker-compose logs postgres`
- Ensure DATABASE_URL in .env matches postgres credentials

## Best Practices

1. **Always test in dev first** - Never push untested changes to main
2. **Use meaningful commit messages** - They appear in deployment logs
3. **Monitor the first deployment** - Watch the Actions tab during your first deployment
4. **Keep backups** - The auto-backup system keeps 10 backups, but you can manually archive important ones
5. **Separate environment files** - Production .env should have different secrets than dev
6. **Review changes before pushing** - Use `git diff` to verify what you're deploying

## Security Considerations

- ✅ Self-hosted runner runs only on your production laptop
- ✅ Secrets are stored in production .env, not in git
- ✅ .env is in .gitignore
- ✅ Runner has same permissions as your user account
- ✅ Workflow only triggers from main branch (you control)

## Next Steps

After setup is complete:

1. Test a deployment with a small change
2. Verify all services are working
3. Set up monitoring/alerting (optional)
4. Document any custom configurations specific to your setup
