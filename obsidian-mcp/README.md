# Obsidian MCP Server

MCP (Model Context Protocol) server for Obsidian vault integration with Open WebUI. Provides AI-powered access to your Obsidian knowledge base with full wiki-link resolution, frontmatter support, and file watching.

## Features

- **Full CRUD Operations**: Create, read, update, delete notes
- **Smart Search**: Full-text search with tag filtering
- **Wiki-link Resolution**: Automatic resolution of `[[Note Name]]` links
- **Frontmatter Support**: Parse and manage YAML frontmatter metadata
- **File Watching**: Automatic cache invalidation on external changes
- **Tag Management**: List and filter by tags
- **Read-only Safety**: Vault mounted read-only by default to prevent accidental changes

## Architecture

- **Python 3.11** with FastAPI framework
- **MCP Python SDK** for standards-compliant protocol implementation
- **Watchdog** for file system monitoring
- **LRU Cache** for performance optimization
- **Pydantic** for configuration validation

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Required: Path to your Obsidian vault
# Dev: Absolute path on host (e.g., /Users/username/Documents/Obsidian/Vault)
# Prod: Path within container (e.g., /vault)
OBSIDIAN_VAULT_PATH=/path/to/your/vault

# Required: API key for authentication (already configured for MCP)
MCP_API_KEY=your-secret-api-key
```

### Docker Compose Setup

#### Development Environment

For local development with direct vault access:

```yaml
# In docker-compose.yml
volumes:
  - ${OBSIDIAN_VAULT_PATH}:/vault:ro  # Mount local directory
```

Set in `.env`:
```bash
OBSIDIAN_VAULT_PATH=/Users/larshansen/Documents/Privat/Obsidian/Private Vault
```

#### Production Environment

For production with Syncthing:

```yaml
# In docker-compose.yml
volumes:
  # - ${OBSIDIAN_VAULT_PATH}:/vault:ro  # Comment out dev
  - syncthing-data:/vault:ro             # Uncomment prod
```

Set in `.env`:
```bash
OBSIDIAN_VAULT_PATH=/vault  # Path within syncthing-data volume
```

## MCP Tools

The server exposes the following MCP tools:

### Notes Management

1. **`create_note`** - Create a new note
   - Parameters: `title`, `content`, `tags` (optional)
   - Returns: Created note metadata

2. **`update_note`** - Update existing note
   - Parameters: `file_path`, `content` (optional)
   - Returns: Updated note metadata

3. **`delete_note`** - Delete a note
   - Parameters: `file_path`
   - Returns: Success confirmation

4. **`append_to_note`** - Append content to note
   - Parameters: `file_path`, `content`
   - Returns: Updated note metadata

### Discovery & Search

5. **`search_notes`** - Search notes by content and tags
   - Parameters: `query`, `tags` (optional), `limit` (default: 50)
   - Returns: List of matching notes with context

6. **`list_notes`** - List all notes
   - Parameters: `tags` (optional), `limit` (default: 100)
   - Returns: List of notes with metadata

7. **`get_note_by_title`** - Find note by title
   - Parameters: `title`
   - Returns: Full note content

### Wiki-links & Tags

8. **`resolve_wiki_link`** - Resolve `[[Link]]` to file path
   - Parameters: `link_name`
   - Returns: Resolved file path

9. **`list_tags`** - List all tags in vault
   - Returns: Tags with usage counts

## Health Check Endpoints

### `/health`
Public health check endpoint (no authentication required)

```bash
curl http://localhost:8001/health
```

Returns:
```json
{
  "status": "healthy",
  "vault": {
    "path": "/vault",
    "total_notes": 150,
    "total_size_mb": 2.5
  },
  "cache": {
    "size": 42,
    "hits": 156,
    "hit_rate_percent": 87.5
  },
  "watcher": {
    "running": true
  }
}
```

### `/vault/stats`
Detailed statistics (requires API key)

```bash
curl -H "Authorization: Bearer $MCP_API_KEY" \
  http://localhost:8001/vault/stats
```

### `/cache/clear`
Clear cache (requires API key)

```bash
curl -X POST \
  -H "Authorization: Bearer $MCP_API_KEY" \
  http://localhost:8001/cache/clear
```

## Deployment

### Via Docker Compose

```bash
# Build and start
docker compose up -d obsidian-mcp

# Check logs
docker compose logs -f obsidian-mcp

# Check health
curl http://localhost:8001/health
```

### Via Deploy Script

```bash
# Automated deployment
./scripts/deploy.sh
```

The deploy script will:
1. Validate environment variables
2. Build the container
3. Start the service
4. Verify health

## Development

### Local Testing

```bash
# Install dependencies
cd obsidian-mcp
pip install -r requirements.txt

# Set environment variables
export OBSIDIAN_VAULT_PATH="/path/to/vault"
export MCP_API_KEY="test-key"

# Run server
python -m app.main
```

### Running Tests

```bash
# TODO: Add pytest tests
pytest
```

## Troubleshooting

### Container Fails to Start

Check logs:
```bash
docker compose logs obsidian-mcp
```

Common issues:
- **Vault path doesn't exist**: Verify `OBSIDIAN_VAULT_PATH` is correct
- **No .md files found**: Vault must contain at least one markdown file
- **Permission denied**: Check file permissions on vault directory

### Cache Issues

Clear cache manually:
```bash
curl -X POST \
  -H "Authorization: Bearer $MCP_API_KEY" \
  http://localhost:8001/cache/clear
```

Or restart the container:
```bash
docker compose restart obsidian-mcp
```

### File Watcher Not Working

The file watcher monitors the vault for external changes. If changes aren't being detected:

1. Check watcher status:
   ```bash
   curl http://localhost:8001/health | jq '.watcher'
   ```

2. Restart the service:
   ```bash
   docker compose restart obsidian-mcp
   ```

## Security Considerations

- **Read-only Mount**: Vault is mounted read-only (`:ro`) to prevent accidental data loss
- **API Key Authentication**: All endpoints except `/health` require Bearer token auth
- **Path Traversal Protection**: All file paths are validated to prevent escaping vault
- **File Size Limits**: Configurable max file size (default: 10MB)
- **Resource Limits**: Container has memory (256MB) and CPU (0.25) limits

## Performance

- **LRU Cache**: In-memory cache with configurable size (default: 1000 items)
- **Cache TTL**: 5 minutes default, shorter for search results
- **File Watching**: Debounced to prevent thrashing on bulk changes
- **Lazy Loading**: Wiki-link resolution map built on-demand

## Integration with Open WebUI

The Obsidian MCP server is automatically registered with Open WebUI via `TOOL_SERVER_CONNECTIONS`:

```yaml
{
  "type": "openapi",
  "url": "http://obsidian-mcp:8000",
  "auth_type": "bearer",
  "key": "${MCP_API_KEY}",
  "config": { "enable": true },
  "info": {
    "id": "obsidian-vault",
    "name": "Obsidian Vault",
    "description": "Read, create, update, and search Obsidian vault notes"
  }
}
```

### Enabling in Open WebUI

1. Go to **Settings** → **Tools**
2. Find **Obsidian Vault** in the list
3. Enable the tool for your desired models
4. Start using Obsidian commands in your chats!

## License

Part of the Open WebUI project. See main repository for license information.

## Sources

- [mcp · PyPI](https://pypi.org/project/mcp/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [python-frontmatter](https://pypi.org/project/python-frontmatter/)
- [watchdog](https://pypi.org/project/watchdog/)
- [Pydantic](https://docs.pydantic.dev/)
