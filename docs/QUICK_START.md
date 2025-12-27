# Quick Start: Production Deployment

## TL;DR - Get Started in 5 Minutes

### 1. Install GitHub Actions Runner (Production Laptop)

```bash
# Go to: https://github.com/<your-repo>/settings/actions/runners
# Click "New self-hosted runner" and run the commands shown, then:

cd ~/actions-runner
sudo ./svc.sh install
sudo ./svc.sh start
```

### 2. Make Scripts Executable (Production Laptop)

```bash
cd /path/to/production/openwebui
chmod +x scripts/*.sh
```

### 3. Test It Works (Production Laptop)

```bash
./scripts/backup.sh   # Should create backups/backup-YYYYMMDD-HHMMSS/
./scripts/deploy.sh   # Should restart all services successfully
```

### 4. Deploy from Dev (Your Dev Machine)

```bash
# Make a change, any change (e.g., add a comment to docker-compose.yml)
git add .
git commit -m "Test deployment pipeline"
git push origin main

# Watch it deploy: https://github.com/<your-repo>/actions
```

That's it! 🎉

---

## Development → Production Workflow

```
┌─────────────────┐
│ Dev Environment │
│  (Local Clone)  │
└────────┬────────┘
         │
         │ 1. Make changes
         │ 2. Test locally
         │ 3. git push origin main
         ▼
┌─────────────────┐
│     GitHub      │
│  (main branch)  │
└────────┬────────┘
         │
         │ Triggers workflow
         ▼
┌─────────────────┐
│ Self-hosted     │
│ Runner (Prod)   │
└────────┬────────┘
         │
         │ Runs:
         │ - backup.sh
         │ - deploy.sh
         ▼
┌─────────────────┐
│   Production    │
│ ✅ Updated!     │
│ 💾 Data Safe    │
└─────────────────┘
```

## What Gets Deployed

✅ **Updated**:
- docker-compose.yml
- Dockerfiles
- Environment variables (.env)
- Custom scripts
- Container images

💾 **Preserved** (Never Touched):
- postgres_data/ (your database)
- openwebui_data/ (your app data)
- qdrant_data/ (your vectors)
- ollama_data/ (your models)

## Common Commands

```bash
# Manual deployment (production)
cd /path/to/production/openwebui
./scripts/deploy.sh

# Backup before changes (production)
./scripts/backup.sh

# View service status (production)
docker-compose ps
docker-compose logs -f openwebui

# Rollback (production)
# 1. Find backup: ls -lt backups/
# 2. Restore: cp backups/backup-YYYYMMDD-HHMMSS/* .
# 3. Deploy: ./scripts/deploy.sh
```

## Troubleshooting One-Liners

```bash
# Runner not working?
sudo ~/actions-runner/svc.sh status
sudo ~/actions-runner/svc.sh restart

# Services not starting?
docker-compose logs --tail=50

# Check what's running
docker-compose ps

# Nuclear option (if really stuck)
docker-compose down
./scripts/backup.sh
git pull origin main
docker-compose up -d
```

## Full Documentation

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete details.
