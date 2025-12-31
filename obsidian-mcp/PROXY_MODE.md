# Proxy Mode - Dynamic Tool Loading

## Quick Start

### Enable Proxy Mode

Add to `.env`:
```bash
USE_PROXY_MODE=true
```

Restart service:
```bash
docker compose restart obsidian-mcp
```

Verify in logs:
```bash
docker compose logs obsidian-mcp | grep "proxy"
# Should show: "MCP proxy server initialized (3 tools)"
```

## What is Proxy Mode?

Proxy mode reduces model context usage by **93%** while preserving full functionality.

### Before (Direct Mode)
- **23 tools** exposed to model
- Each tool has description + full JSON schema
- **~7,000 characters** of context consumed
- Adding features increases context linearly

### After (Proxy Mode)
- **3 tools** exposed to model
- Minimal descriptions, no schemas
- **~450 characters** of context consumed
- Adding features doesn't increase context

## The 3 Proxy Tools

### 1. obsidian_lookup

**Purpose:** Discover what action to use

**Usage:**
```json
{
  "tool": "obsidian_lookup",
  "args": {
    "intent": "search for notes about AI"
  }
}
```

**Returns:**
- Action name
- Required and optional fields
- Defaults and limits
- Confidence score

### 2. obsidian

**Purpose:** Execute vault operations

**Usage:**
```json
{
  "tool": "obsidian",
  "args": {
    "action": "search_notes",
    "args": {
      "query": "AI",
      "limit": 10
    }
  }
}
```

**Returns:**
- Success/failure status
- Action result
- Error details (if failed)

### 3. obsidian_help

**Purpose:** Get on-demand help

**Usage:**
```json
{
  "tool": "obsidian_help",
  "args": {
    "topic": "core",
    "verbosity": "short"
  }
}
```

**Topics:**
- `overview` - General overview
- `core` - Main operations
- `search` - Search/list
- `read` - Reading operations
- `write` - Writing operations
- `templates` - Templates
- `graph` - Knowledge graph
- `admin` - Admin functions

## Usage Patterns

### Pattern 1: Lookup → Execute

```
1. Use obsidian_lookup("search for notes")
   → Returns: action="search_notes", fields=[query, limit, tags, use_regex]

2. Use obsidian(action="search_notes", args={query: "AI"})
   → Returns: {count: 5, results: [...]}
```

### Pattern 2: Direct Execute

If you know the action:
```
Use obsidian(action="create_note", args={title: "X", content: "Y"})
→ Returns: {success: true, path: "X.md"}
```

### Pattern 3: Help First

When unsure:
```
1. Use obsidian_help(topic="core")
   → See what's available

2. Use obsidian_lookup("create a note")
   → Get specific action details

3. Use obsidian(action="create_note", args={...})
   → Execute
```

## All Available Actions

### Core Bundle (15 actions)
- **search_notes** - Search by content/tags
- **list_notes** - List with filtering
- **get_note** - Get metadata only
- **read_note_content** - Read full content
- **create_note** - Create new note
- **update_note** - Update existing
- **append_note** - Append content
- **delete_note** - Delete note
- **move_note** - Move/rename
- **resolve_link** - Resolve wiki-links
- **get_toc** - Table of contents
- **read_section** - Read by heading
- **update_section** - Update by heading
- **read_block** - Read by ^block-id
- **update_block** - Update by ^block-id

### Knowledge Bundle (4 actions)
- **get_backlinks** - Notes linking here
- **get_orphans** - Orphaned notes
- **get_graph** - Knowledge graph
- **list_tags** - All tags with counts

### Templates Bundle (4 actions)
- **list_templates** - Available templates
- **create_from_template** - Use template
- **save_template** - Save new template
- **delete_template** - Remove template

### Admin Bundle (4 actions)
- **health_check** - Server health
- **get_stats** - Vault statistics
- **clear_cache** - Clear caches
- **get_daily_note** - Daily note operations

## Examples

### Search Notes
```json
// Lookup
{"tool": "obsidian_lookup", "args": {"intent": "find notes about Python"}}

// Execute
{"tool": "obsidian", "args": {
  "action": "search_notes",
  "args": {"query": "Python", "limit": 10}
}}
```

### Create Note
```json
// Direct (no lookup needed)
{"tool": "obsidian", "args": {
  "action": "create_note",
  "args": {
    "title": "My Ideas",
    "content": "# Ideas\n\n- Idea 1\n- Idea 2",
    "tags": ["brainstorm"]
  }
}}
```

### Get Backlinks
```json
// Lookup
{"tool": "obsidian_lookup", "args": {"intent": "what links to my note"}}

// Execute
{"tool": "obsidian", "args": {
  "action": "get_backlinks",
  "args": {"title": "Project Plan"}
}}
```

### Use Template
```json
// Execute
{"tool": "obsidian", "args": {
  "action": "create_from_template",
  "args": {
    "template_name": "meeting-notes",
    "note_path": "meetings/2024-01-15.md",
    "variables": {
      "title": "Team Sync",
      "attendees": "Alice, Bob, Carol"
    }
  }
}}
```

## Performance

Measured on typical vault (~100 notes):

| Operation | Time | Target |
|-----------|------|--------|
| Routing | 2-5ms | <10ms ✓ |
| Lookup | 10-30ms | <50ms ✓ |
| Validation | <5ms | <10ms ✓ |
| Execution | (unchanged) | - |

**Context Savings:** ~93% reduction (~6,550 chars saved)

## Validation & Security

All requests are validated:

1. **Action exists** - Unknown actions rejected
2. **Required fields** - Missing fields rejected
3. **Bundle limits** - Exceeded limits rejected
4. **Input sanitization** - Prevents injection

Example error:
```json
{
  "success": false,
  "error": "Missing required field: query",
  "action": "search_notes",
  "bundle": "core"
}
```

## Limits

| Limit | Default | Maximum |
|-------|---------|---------|
| Search results | 50 | 200 |
| List results | 100 | 500 |
| Graph depth | 1 | 3 |
| Graph nodes | 50 | 200 |
| Template depth | 5 | 5 |

## Testing

Run tests:
```bash
# Unit tests
pytest tests/unit/test_proxy.py -v

# Integration tests
pytest tests/integration/test_proxy_routing.py -v

# Backward compatibility
pytest tests/integration/test_backward_compatibility.py -v

# Performance benchmarks
pytest tests/integration/test_performance.py -v
```

## Troubleshooting

### Check Mode

```bash
docker compose logs obsidian-mcp | grep "MCP.*initialized"

# Proxy mode: "MCP proxy server initialized (3 tools)"
# Direct mode: "MCP direct server initialized (23 tools)"
```

### Enable Debug Logging

```bash
# In .env
LOG_LEVEL=DEBUG
```

### Test Connectivity

```bash
curl http://localhost:8001/health
```

### Common Issues

**"Unknown action"**
- Use obsidian_lookup first to discover action name

**"Missing required field"**
- Check lookup response for required_fields

**"Limit exceeded"**
- Check lookup response for limits, adjust args

**Low confidence routing**
- Be more specific in intent
- Or skip lookup and use direct execution

## Migration from Direct Mode

See [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for detailed migration instructions.

Quick checklist:
1. Add `USE_PROXY_MODE=true` to .env
2. Restart service
3. Update integrations to use 2-step pattern
4. Test basic operations
5. Monitor logs for errors

## Rollback

To disable proxy mode:

```bash
# In .env
USE_PROXY_MODE=false
# Or remove the line

# Restart
docker compose restart obsidian-mcp
```

## Future Features (Phase 3)

Coming soon via proxy mode (no context increase!):
- **Query Bundle** - Dataview-like queries with filters and aggregations
- **Enrichment Bundle** - Automatic content analysis and metadata

## Support

- **Tests:** Run `pytest tests/integration/test_proxy_routing.py -v`
- **Logs:** `docker compose logs obsidian-mcp`
- **Health:** `curl http://localhost:8001/health`
- **Issues:** See GitHub issues
