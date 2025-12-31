# OpenWebUI MCP Proxy Configuration

## Problem

OpenWebUI was configured to use the **old direct API** (`/tools/*` endpoints with 23 individual tools), bypassing the **new MCP proxy** with its improvements:
- ❌ No execution IDs
- ❌ No tag normalization
- ❌ No verification markers
- ❌ High context usage (23 tools)

## Solution

Configure OpenWebUI to use the **MCP proxy HTTP bridge** (`/mcp/*` endpoints with 3 tools).

## MCP Proxy HTTP Bridge

The system now exposes the MCP proxy tools via HTTP endpoints:

### Available Endpoints

| Endpoint | Purpose | Replaces |
|----------|---------|----------|
| `POST /mcp/lookup` | Discover what action to use | N/A (new) |
| `POST /mcp/execute` | Execute vault operations | All `/tools/*` endpoints |
| `POST /mcp/help` | Get capability documentation | N/A (new) |
| `GET /mcp/info` | Check proxy status | N/A (new) |

### Why This is Better

✅ **Context reduction** - 3 tools instead of 23 (93% reduction)
✅ **Execution IDs** - Every operation returns unforgeable proof
✅ **Tag normalization** - Automatic `#tag` → `tag` correction
✅ **Better validation** - Multi-layer validation pipeline
✅ **Verification markers** - Timestamps and status indicators
✅ **Warning system** - Clear feedback when tags are normalized

## Configuration Steps

### Step 1: Verify MCP Bridge is Active

```bash
curl http://localhost:8001/mcp/info
```

**Expected response:**
```json
{
    "mode": "proxy",
    "tools": 3,
    "endpoints": {
        "lookup": "/mcp/lookup",
        "execute": "/mcp/execute",
        "help": "/mcp/help"
    },
    "description": "MCP proxy mode reduces model context by 93% while preserving full functionality"
}
```

### Step 2: Update OpenWebUI Tool Configuration

In OpenWebUI, you need to configure it to use the MCP proxy endpoints instead of the direct tools.

#### Option A: Update Function Definitions (Recommended)

Create **3 new custom functions** in OpenWebUI:

**1. obsidian_lookup function:**
```python
"""
type: function
"""
import requests
import json

def obsidian_lookup(intent: str, note_hint: str = None) -> dict:
    """
    Discover what Obsidian action to use for a task.

    Args:
        intent: What you want to do (e.g., "search for notes about AI")
        note_hint: Optional note title hint

    Returns:
        Dictionary with action, required_fields, optional_fields, limits
    """
    url = "http://obsidian-mcp:8000/mcp/lookup"
    headers = {
        "Authorization": "Bearer YOUR_API_KEY_HERE",
        "Content-Type": "application/json"
    }
    data = {"intent": intent}
    if note_hint:
        data["note_hint"] = note_hint

    response = requests.post(url, headers=headers, json=data)
    return response.json()
```

**2. obsidian function:**
```python
"""
type: function
"""
import requests
import json

def obsidian(action: str, args: dict) -> dict:
    """
    Execute an Obsidian vault operation.

    Args:
        action: Action name (use obsidian_lookup to discover)
        args: Action arguments dictionary

    Returns:
        Dictionary with success, result, and optional warnings
    """
    url = "http://obsidian-mcp:8000/mcp/execute"
    headers = {
        "Authorization": "Bearer YOUR_API_KEY_HERE",
        "Content-Type": "application/json"
    }
    data = {
        "action": action,
        "args": args
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()
```

**3. obsidian_help function:**
```python
"""
type: function
"""
import requests
import json

def obsidian_help(topic: str = None, verbosity: str = "short") -> dict:
    """
    Get help about Obsidian capabilities.

    Args:
        topic: Help topic (overview, core, search, read, write, templates, graph, admin)
        verbosity: Detail level (short, normal)

    Returns:
        Dictionary with help content
    """
    url = "http://obsidian-mcp:8000/mcp/help"
    headers = {
        "Authorization": "Bearer YOUR_API_KEY_HERE",
        "Content-Type": "application/json"
    }
    data = {
        "topic": topic,
        "verbosity": verbosity
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()
```

**Important:** Replace `YOUR_API_KEY_HERE` with your actual MCP API key from `.env`

#### Option B: Direct HTTP Configuration

If OpenWebUI supports direct HTTP tool configuration, add:

```json
{
  "name": "obsidian_lookup",
  "description": "YOU HAVE ACCESS to an Obsidian vault. Use this to discover what action to use for vault operations (search, create, update, read notes, etc.). ALWAYS call this when you need to find the right action.",
  "url": "http://obsidian-mcp:8000/mcp/lookup",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer YOUR_API_KEY"
  },
  "parameters": {
    "intent": {
      "type": "string",
      "required": true,
      "description": "What you want to do with the vault"
    },
    "note_hint": {
      "type": "string",
      "required": false,
      "description": "Optional note title hint"
    }
  }
}
```

```json
{
  "name": "obsidian",
  "description": "YOU HAVE ACCESS to an Obsidian vault. Use this to EXECUTE vault operations: list notes, search notes, create notes, update notes, read content, manage tags, etc. You MUST call this tool to perform any vault operation. The tool returns a verification ID proving execution.",
  "url": "http://obsidian-mcp:8000/mcp/execute",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer YOUR_API_KEY"
  },
  "parameters": {
    "action": {
      "type": "string",
      "required": true,
      "description": "Action name (use obsidian_lookup to discover)"
    },
    "args": {
      "type": "object",
      "required": true,
      "description": "Action arguments"
    }
  }
}
```

### Step 3: Remove Old Tool Configurations

Remove or disable all the old `/tools/*` endpoints:
- `/tools/create_note`
- `/tools/update_note`
- `/tools/search_notes`
- ... (all 23 old endpoints)

### Step 4: Test the Configuration

In OpenWebUI chat, try:

```
List notes in my vault
```

**Expected behavior:**
1. LLM calls `obsidian_lookup(intent="list all notes")`
2. Gets back: `action="list_notes"`, `required_fields=[]`
3. LLM calls `obsidian(action="list_notes", args={})`
4. Gets back results with **execution ID** and **timestamp**

## Verification

### Check Execution IDs

When the LLM performs an operation, it should reference an execution ID:

```
✅ Done. I've added the tag to the note (execution ID: a3f9d82c)
```

### Check Tag Normalization

If you add a tag with `#`:

```
User: Add tag #architecture to the note
AI: ✅ Done (execution ID: b7e2f159)

    ⚠️ Tag Normalization:
       - Normalized '#architecture' to 'architecture'

    Note: Frontmatter tags should NOT have # prefix.
```

### Check Logs

```bash
docker compose logs obsidian-mcp --tail=50 | grep "mcp"
```

Should show:
- `MCP proxy server initialized (3 tools)`
- `MCP HTTP bridge enabled at /mcp/*`
- HTTP requests to `/mcp/lookup` and `/mcp/execute`

## Troubleshooting

### Old Endpoints Still Being Called

**Symptom:** Logs show `POST /tools/update_note` instead of `POST /mcp/execute`

**Fix:** OpenWebUI is still configured to use old endpoints. Update function definitions as shown above.

### "MCP proxy not initialized" Error

**Symptom:** `/mcp/*` endpoints return 503 error

**Fix:** Check that `USE_PROXY_MODE=true` in `.env` and container was restarted.

### Tags Still Not Working

**Symptom:** Tags with `#` prefix aren't being added correctly

**Cause:** Still using old `/tools/*` endpoints (they now have normalization too, but MCP proxy is preferred)

**Fix:** Configure OpenWebUI to use `/mcp/execute` endpoint.

### No Execution IDs

**Symptom:** Operations complete but no execution ID shown

**Cause:** Using old direct endpoints

**Fix:** Switch to MCP proxy endpoints.

## Benefits of Using MCP Proxy

| Feature | Old Direct API | New MCP Proxy |
|---------|----------------|---------------|
| Tools exposed | 23 | 3 |
| Context usage | ~7,000 chars | ~450 chars |
| Execution IDs | ❌ No | ✅ Yes |
| Tag normalization | ✅ Yes (now) | ✅ Yes |
| Verification markers | ❌ No | ✅ Yes |
| Warnings | ❌ No | ✅ Yes |
| Two-step pattern | ❌ N/A | ✅ lookup → execute |
| Future scalability | ❌ Linear growth | ✅ Zero growth |

## Example Workflow

### Using MCP Proxy (Recommended)

```
1. User: "Add the architecture tag to the multi-tenancy note"

2. LLM calls:
   obsidian_lookup(intent="add tag to note")

3. Response:
   {
     "action": "update_note",
     "required_fields": ["file_path"],
     "optional_fields": ["content", "frontmatter"],
     ...
   }

4. LLM calls:
   obsidian(action="update_note", args={
     "file_path": "tech/architecture/multi-tenancy.md",
     "frontmatter": {"tags": ["tech", "architecture"]}
   })

5. Response:
   {
     "success": true,
     "action": "update_note",
     "bundle": "core",
     "result": {
       "path": "tech/architecture/multi-tenancy.md",
       ...
     },
     "execution_id": "a3f9d82c",
     "timestamp": "14:32:45"
   }

6. LLM to user:
   "✅ Done. I've added the architecture tag to the note (execution ID: a3f9d82c)"
```

### Using Old Direct API (Not Recommended)

```
1. User: "Add the architecture tag to the multi-tenancy note"

2. LLM calls:
   POST /tools/update_note
   {
     "file_path": "tech/architecture/multi-tenancy.md",
     "frontmatter": {"tags": ["tech", "architecture"]}
   }

3. Response:
   {
     "success": true,
     "note": {...}
   }
   (No execution ID, no verification)

4. LLM to user:
   "✅ Done. I've added the tag."
   (But did it really? No proof!)
```

## Summary

✅ **Configure OpenWebUI to use `/mcp/*` endpoints**
✅ **Remove old `/tools/*` endpoint configurations**
✅ **Verify execution IDs appear in responses**
✅ **Check tag normalization warnings work**

This gives you:
- 93% context reduction
- Unforgeable execution proof
- Automatic tag normalization
- Better error handling
- Future-proof architecture
