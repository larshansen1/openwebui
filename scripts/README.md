# Deployment Scripts

This directory contains automation scripts for Open WebUI deployment and maintenance.

## MCP Configuration Scripts

### verify-mcp-config.sh
Verifies that MCP tool servers are properly configured and accessible.

**Usage:**
```bash
./scripts/verify-mcp-config.sh
```

**What it checks:**
- MCP server is reachable with the configured API key
- Open WebUI container can connect to MCP server
- All tool endpoints (time, brave-search, fetch) are accessible

**Exit codes:**
- 0: All checks passed
- 1: Configuration error detected

### reset-tool-config.sh
Resets the tool server configuration stored in the database, forcing Open WebUI to re-initialize from the `TOOL_SERVER_CONNECTIONS` environment variable.

**When to use:**
- After changing `MCP_API_KEY` in .env
- When tools show "Invalid API key" errors
- After updating `TOOL_SERVER_CONNECTIONS` configuration

**Usage:**
```bash
./scripts/reset-tool-config.sh
docker compose restart openwebui
```

## Why These Scripts Are Needed

Open WebUI stores `TOOL_SERVER_CONNECTIONS` as a "PersistentConfig" in the PostgreSQL database on first startup. Subsequent restarts **ignore** the environment variable and use the stored database value.

This means:
1. If the API key changes in `.env`
2. Or if `TOOL_SERVER_CONNECTIONS` is updated
3. **You must reset the database config** for changes to take effect

## CI/CD Integration

The GitHub Actions workflow automatically:
1. Deploys the latest configuration
2. Verifies MCP tool servers work
3. If verification fails, resets the config and retries
4. Ensures production always has working MCP tools

See `.github/workflows/deploy-production.yml` for the automation.

## Troubleshooting

**Tools show "Invalid API key" error:**
```bash
./scripts/verify-mcp-config.sh
```

If verification fails:
```bash
./scripts/reset-tool-config.sh
docker compose restart openwebui
./scripts/verify-mcp-config.sh  # Verify fix worked
```

**MCP_API_KEY mismatch:**
Check that the same key is used in:
- `.env` file (`MCP_API_KEY=...`)
- MCP server environment (in docker-compose.yml)
- Open WebUI environment (in docker-compose.yml)
