# Deployment Scripts

This directory contains automation scripts for Open WebUI deployment and maintenance.

## MCP Configuration Scripts

### verify-mcp-config.sh
Verifies that MCP tool servers are properly configured and working.

**Usage:**
```bash
./scripts/verify-mcp-config.sh
```

**What it checks:**
- `MCP_API_KEY` is set in `.env`
- MCP server is reachable with the configured API key
- `TOOL_SERVER_CONNECTIONS` environment variable is set in OpenWebUI container  
- API keys match between `.env` and running containers
- OpenWebUI is responding
- Actual tool functionality works (calls a test tool)

**Exit codes:**
- 0: All checks passed
- 1: Configuration error detected (likely env var mismatch)

### reset-tool-config.sh
Recreates OpenWebUI and MCP server containers to reload environment variables from `.env`.

**When to use:**
- After changing `MCP_API_KEY` in .env
- After updating `TOOL_SERVER_CONNECTIONS` in docker-compose.yml
- When verification script reports "API key mismatch"

**Usage:**
```bash
./scripts/reset-tool-config.sh
```

## Critical Understanding: Docker Compose and Environment Variables

**IMPORTANT:** `docker compose restart` does NOT reload environment variables from `.env`!

When you change `.env`, you must either:
1. Use `docker compose up -d --force-recreate <service>` to recreate specific containers
2. Use `docker compose down && docker compose up -d` to recreate all containers

This is why the reset script uses `--force-recreate`.

## How TOOL_SERVER_CONNECTIONS Works

`TOOL_SERVER_CONNECTIONS` is read from environment variables when the container starts:

1. Docker Compose reads `.env` file
2. Substitutes `${MCP_API_KEY}` in docker-compose.yml  
3. Passes the complete JSON to the container as an environment variable
4. OpenWebUI reads `TOOL_SERVER_CONNECTIONS` on startup

**No database storage** - it's purely environment-based.

## Common Production Issue

**Symptom:** Tools show "Invalid API key" error after updating `.env`

**Cause:** Containers still have old environment variables

**Root cause:** Someone ran `docker compose restart` instead of recreating containers

**Fix:**
```bash
./scripts/reset-tool-config.sh
```

Or manually:
```bash
docker compose up -d --force-recreate openwebui mcp-server
```

## CI/CD Integration

The GitHub Actions workflow automatically:
1. Deploys the latest configuration (runs deploy.sh)
2. Verifies MCP tool configuration
3. If verification fails (API key mismatch), recreates containers
4. Verifies again to ensure fix worked
5. Fails deployment if tools still don't work

See `.github/workflows/deploy-production.yml` for details.

## Troubleshooting

**Tools show "Invalid API key" error:**
```bash
./scripts/verify-mcp-config.sh
```

This will pinpoint the exact issue.

**After changing MCP_API_KEY:**
```bash
./scripts/reset-tool-config.sh
./scripts/verify-mcp-config.sh
```

**Check what key containers actually have:**
```bash
docker exec openwebui env | grep MCP_API_KEY
docker exec openwebui-mcp-server env | grep MCP_API_KEY
```
