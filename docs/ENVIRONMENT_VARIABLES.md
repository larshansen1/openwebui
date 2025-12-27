# Environment Variable Management

## Overview

Environment variables differ between dev and production, but their structure must stay in sync. This guide explains how to manage them properly.

## File Structure

```
.env.template       # In git - documents all variables (no secrets)
.env                # NOT in git - contains actual secrets
.env.local          # NOT in git - optional local overrides
```

## The Rules

### ✅ DO

1. **Always update `.env.template` when adding new variables**
2. **Add documentation to `.env.template`** (what it does, how to generate it)
3. **Run validation before deploying** (`./scripts/validate-env.sh`)
4. **Keep production and dev `.env` files separate** (never share secrets)
5. **Commit `.env.template` to git**

### ❌ DON'T

1. **Never commit `.env` to git** (contains secrets!)
2. **Never hardcode secrets in docker-compose.yml**
3. **Never share production `.env` file** (not even via Slack/email)
4. **Never skip validation** (catch missing vars early)

## Workflow: Adding a New Environment Variable

### Step 1: Add to docker-compose.yml

```yaml
openwebui:
  environment:
    # ... existing vars
    NEW_FEATURE_API_KEY: ${NEW_FEATURE_API_KEY}
```

### Step 2: Update .env.template

```bash
# In .env.template, add documentation:

# New Feature API Key
# Description: API key for the new feature integration
# Required: Yes (No for optional features)
# How to get: Sign up at https://example.com/api
# Command to generate (if applicable): openssl rand -base64 32
NEW_FEATURE_API_KEY=
```

### Step 3: Update validation script

Edit `scripts/validate-env.sh`:

```bash
# If required, add to REQUIRED_VARS:
REQUIRED_VARS=(
    "POSTGRES_PASSWORD"
    "WEBUI_SECRET_KEY"
    "RAG_EMBEDDING_MODEL"
    "MCP_API_KEY"
    "NEW_FEATURE_API_KEY"  # ← Add here
)

# If optional, add to RECOMMENDED_VARS:
RECOMMENDED_VARS=(
    "OPENAI_API_KEY"
    "QDRANT_API_KEY"
    "BRAVE_API_KEY"
    "NEW_FEATURE_API_KEY"  # ← Or add here
)
```

### Step 4: Update your local .env files

**On dev machine:**
```bash
cd ~/Documents/Dev/Docker/openwebui
echo "NEW_FEATURE_API_KEY=dev-test-key-12345" >> .env
```

**On production:**
```bash
cd /home/admin/docker/openwebui
echo "NEW_FEATURE_API_KEY=prod-real-key-67890" >> .env
```

### Step 5: Commit and test

```bash
# Validate locally first
./scripts/validate-env.sh

# If validation passes, commit
git add .env.template docker-compose.yml scripts/validate-env.sh
git commit -m "Add NEW_FEATURE_API_KEY for new feature"

# Test on dev
docker compose up -d

# Push to trigger production deployment
git push origin main
```

### Step 6: Production deployment validation

The deployment will:
1. ✅ Pull latest code (including updated `.env.template`)
2. ✅ Run `validate-env.sh` to check for NEW_FEATURE_API_KEY
3. ❌ **FAIL if variable is missing** (deployment stops)
4. 📧 You'll get notified to add the variable

If validation fails:
```bash
# SSH to production
ssh production-server

# Add the missing variable
cd /home/admin/docker/openwebui
echo "NEW_FEATURE_API_KEY=prod-real-key" >> .env

# Manually trigger deployment
./scripts/deploy.sh

# Or re-run from GitHub Actions (manual trigger)
```

## Current Variables

### Required Variables

| Variable | Purpose | How to Generate |
|----------|---------|-----------------|
| `POSTGRES_PASSWORD` | Database password | `openssl rand -base64 32` |
| `WEBUI_SECRET_KEY` | JWT signing | `openssl rand -hex 32` |
| `RAG_EMBEDDING_MODEL` | Ollama model name | `all-minilm` or `nomic-embed-text` |
| `MCP_API_KEY` | MCP server auth | `openssl rand -base64 32` |

### Optional Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENAI_API_KEY` | OpenRouter API access | None (features disabled) |
| `QDRANT_API_KEY` | Vector DB auth | None (no auth) |
| `BRAVE_API_KEY` | Web search | None (search disabled) |

## Validation Script

Run anytime to check your environment:

```bash
./scripts/validate-env.sh
```

**Output:**
```
==================================================
Validating Environment Variables
==================================================

Checking required variables:
  ✓ POSTGRES_PASSWORD - Set
  ✓ WEBUI_SECRET_KEY - Set
  ✓ RAG_EMBEDDING_MODEL - Set
  ✓ MCP_API_KEY - Set

Checking recommended variables:
  ✓ OPENAI_API_KEY - Set
  ⚠ QDRANT_API_KEY - Not set (optional)
  ✓ BRAVE_API_KEY - Set

==================================================
⚠️  Warning: Some recommended variables are not set

Missing recommended variables:
  - QDRANT_API_KEY

Your deployment will work, but some features may be disabled.
✅ Environment validation passed!
==================================================
```

## Handling Secrets Across Environments

### Development
- Use **fake/test values** for API keys when possible
- Use **weak passwords** (it's local, security doesn't matter)
- Use **same values for all devs** (consistency)

### Production
- Use **real API keys** from production accounts
- Use **strong passwords** (`openssl rand -base64 32`)
- Use **unique values** (never copy from dev)

## Example: .env Files

### Development (.env)
```bash
POSTGRES_PASSWORD=devpassword123
WEBUI_SECRET_KEY=dev-secret-key-not-secure
OPENAI_API_KEY=sk-test-dev-key-fake
QDRANT_API_KEY=
BRAVE_API_KEY=
RAG_EMBEDDING_MODEL=all-minilm
MCP_API_KEY=dev-mcp-key
```

### Production (.env)
```bash
# NEVER put real values here! This is just an example structure.
# Generate actual secrets using the commands in .env.template

POSTGRES_PASSWORD=<generate with: openssl rand -base64 32>
WEBUI_SECRET_KEY=<generate with: openssl rand -hex 32>
OPENAI_API_KEY=<your actual API key from OpenRouter>
QDRANT_API_KEY=<generate with: openssl rand -base64 32>
BRAVE_API_KEY=<your actual API key from Brave>
RAG_EMBEDDING_MODEL=all-minilm
MCP_API_KEY=<generate with: openssl rand -base64 32>
```

## Troubleshooting

### Deployment fails with "variable not found"

```bash
# On production:
cd /home/admin/docker/openwebui

# Check what's missing
./scripts/validate-env.sh

# Compare with template
diff .env .env.template

# Add missing variables
nano .env
```

### Variable added but still not working

```bash
# Restart containers to pick up new env vars
docker compose down
docker compose up -d

# Or use the deploy script
./scripts/deploy.sh
```

### Accidentally committed .env to git

```bash
# Remove from git (keeps local file)
git rm --cached .env

# Rotate ALL secrets immediately!
# Generate new values for:
# - POSTGRES_PASSWORD
# - WEBUI_SECRET_KEY
# - MCP_API_KEY
# - All API keys

# Update .env with new secrets
# Deploy to production with new secrets
```

## Best Practices

1. **Document everything** - Future you will thank you
2. **Validate early** - Catch errors before production
3. **Use templates** - .env.template is your source of truth
4. **Rotate secrets** - Change passwords periodically
5. **Never share** - Secrets stay out of git, Slack, email
6. **Test locally** - Validate on dev before pushing
7. **Monitor failures** - Watch deployment logs for validation errors

## See Also

- [.env.template](../.env.template) - Template with all variables
- [scripts/validate-env.sh](../scripts/validate-env.sh) - Validation script
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment process
