# MCP Server Setup for Open WebUI

This setup uses [mcpo](https://github.com/open-webui/mcpo) to expose MCP (Model Context Protocol) servers as OpenAPI-compatible HTTP endpoints that can be used with Open WebUI.

## What's Included

The docker-compose setup includes **multiple MCP servers running in a single container**, configured via `mcp_config/config.template.json`:

- **time server** - Time and timezone utilities
- **fetch server** - HTTP fetch capabilities
- **brave-search** - Web search (requires API key)

## Quick Start

1. **Configure API Keys (Optional):**
   Edit `.env` and set:
   ```
   MCP_API_KEY=your-secret-key
   BRAVE_API_KEY=your-brave-api-key  # Only if using brave-search
   ```

2. **Start the MCP server:**
   ```bash
   docker compose up -d mcp-server
   ```

3. **Verify it's running:**
   ```bash
   # Check time server
   curl http://localhost:8000/time/docs

   # Check fetch server
   curl http://localhost:8000/fetch/docs
   ```

4. **Test the API:**
   ```bash
   curl -H "Authorization: Bearer mcp-secret-key-change-me" \
        -H "Content-Type: application/json" \
        -d '{"timezone": "UTC"}' \
        http://localhost:8000/time/get_current_time
   ```

## Configuration

### Environment Variables

The MCP server uses these environment variables from your `.env` file:

- `MCP_API_KEY`: API key for securing the MCP server endpoints (default: `mcp-secret-key-change-me`)

### Changing the API Key

Edit your `.env` file and change the `MCP_API_KEY` value, then restart the service:
```bash
docker-compose restart mcp-server
```

## Available Endpoints

With multiple servers, each is mounted at its own subpath:

- **Time Server**:
  - Docs: http://localhost:8000/time/docs
  - Tools: `/get_current_time`, `/convert_time`

- **Fetch Server**:
  - Docs: http://localhost:8000/fetch/docs
  - Tools: `/fetch`

- **Brave Search** (if API key configured):
  - Docs: http://localhost:8000/brave-search/docs

## Adding More MCP Servers

To add more MCP servers, simply edit `mcp_config/config.template.json`:

```json
{
  "mcpServers": {
    "time": {
      "command": "uvx",
      "args": ["mcp-server-time", "--local-timezone=UTC"]
    },
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"]
    },
    "weather": {
      "command": "uvx",
      "args": ["mcp-server-weather"]
    },
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem", "/data"]
    },
    "github": {
      "command": "uvx",
      "args": ["mcp-server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

### Adding Environment Variables for New Servers

If a server requires API keys or tokens:

1. **Add the variable to `.env`:**
   ```bash
   GITHUB_TOKEN=your_github_token_here
   ```

2. **Update `mcp-entrypoint.sh`** to substitute the new variable:
   ```python
   config = config.replace('${GITHUB_TOKEN}', os.environ.get('GITHUB_TOKEN', ''))
   ```

3. **Add the environment variable to docker-compose.yml:**
   ```yaml
   environment:
     GITHUB_TOKEN: ${GITHUB_TOKEN:-}
   ```

4. **Restart the container:**
   ```bash
   docker compose restart mcp-server
   ```

## Integrating with Open WebUI

Once your MCP servers are running, configure Open WebUI to use them:

### Method 1: Via Settings → Tools (Recommended)

1. **Open Settings:**
   - Click on your profile (bottom left)
   - Select **Settings**

2. **Add OpenAPI Tools:**
   - Go to **Tools** section
   - Click to add a new OpenAPI server
   - Add each MCP server separately:
     - **Time Server**: `http://mcp-server:8000/time`
     - **Fetch Server**: `http://mcp-server:8000/fetch`
     - **Brave Search**: `http://mcp-server:8000/brave-search` (if configured)
   - API Key: `mcp-secret-key-change-me` (or your `MCP_API_KEY` value)

3. **Enable Tools for Models:**
   - Go to **Workspace → Models**
   - Select your model (e.g., GPT-5.2)
   - Click the edit/pencil icon
   - Scroll to **Tools** section
   - Check the MCP tools you want to enable
   - **Set Function Calling Mode to "Native"** for best results
   - Save

### Method 2: Via Admin Panel (Alternative)

If you have admin access:
- **Admin Panel → Settings → Connections → OpenAI**
- Add as OpenAI-compatible API connection
- This makes tools available to all users

## Architecture Benefits

This setup uses a **single container** to run multiple MCP servers:

✅ **Efficient**: One container instead of one per tool
✅ **Centralized**: All tools use the same API key
✅ **Easy to manage**: Add tools by editing one config file
✅ **Secure**: API keys injected from environment variables
✅ **Flexible**: Each server mounted at its own subpath

## Troubleshooting

### Check MCP Server Logs
```bash
docker-compose logs mcp-server
```

### Verify Network Connectivity
```bash
docker exec openwebui curl http://mcp-server:8000/health
```

### Test API Authentication
```bash
curl -H "Authorization: Bearer your-api-key" http://localhost:8000/docs
```

## Available MCP Servers

Some popular MCP servers you can try:

- `mcp-server-time`: Time and timezone utilities
- `mcp-server-weather`: Weather information
- `mcp-server-filesystem`: File system operations
- `mcp-server-github`: GitHub integration
- `mcp-server-fetch`: HTTP fetch utilities
- `mcp-server-sqlite`: SQLite database operations

## Resources

- [MCPO Documentation](https://github.com/open-webui/mcpo)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [Open WebUI Documentation](https://docs.openwebui.com)
