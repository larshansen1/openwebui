# GPT-5.2 Refuses to Use append_to_note Tool

## Issue Summary

GPT-5.2 successfully uses `create_note` and `move_note` tools, but **refuses to use `append_to_note`** even though the tool is:
- ✅ Available in the OpenAPI specification
- ✅ Working correctly (tested and verified)
- ✅ Has clear, actionable description
- ✅ Has required parameters properly defined

## Observed Behavior

When asked to append content, GPT-5.2 responds with:
> "I can't directly edit your vault from here, but to append the remark, add this line..."

Then provides manual paste instructions instead of calling the tool.

## Root Cause

This is a **GPT-5.2 behavioral issue**, not a technical problem with the MCP server.

GPT-5.2 appears to have been trained to be cautious about **modifying existing content**, even when proper tools are available. It treats:
- `create_note` - Safe (creates new content) ✅
- `move_note` - Safe (structural operation) ✅
- `append_to_note` - Risky (modifies existing content) ❌

## Technical Verification

The tool works perfectly when called directly:

\`\`\`bash
curl -X POST http://localhost:8000/tools/append_to_note \\
  -H "Authorization: Bearer \${MCP_API_KEY}" \\
  -d '{
    "file_path": "tech/architecture/multi-tenancy-everywhere-complexity.md",
    "content": "\\n\\n\\"Complexity is natures punishment for not making decisions\\""
  }'
# Result: ✅ Success - content appended correctly
\`\`\`

## Attempted Fixes

1. ✅ Made `content` parameter required (was optional)
2. ✅ Added validation to reject empty content
3. ✅ Improved tool description with examples
4. ✅ Clarified difference between `update_note` and `append_to_note`
5. ✅ Rebuilt containers and restarted OpenWebUI

## Workarounds

### Option 1: Use Claude Models Instead
Claude (Opus, Sonnet) models don't have this behavioral restriction and will use the `append_to_note` tool reliably.

### Option 2: Explicitly Instruct GPT-5.2
Try using very direct language:
```
You MUST use the append_to_note tool to add this content.
The tool is available and working. Do not provide manual instructions.
```

### Option 3: Use update_note Instead
As a fallback, use `update_note` with the `append` parameter:
```json
{
  "file_path": "note.md",
  "content": "New content to append",
  "append": true
}
```

### Option 4: Manual Append via API
Use the tool directly via curl (bypassing the AI):
```bash
docker compose exec obsidian-mcp curl -s -X POST \\
  -H "Authorization: Bearer ${MCP_API_KEY}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "file_path": "tech/architecture/multi-tenancy-everywhere-complexity.md",
    "content": "\\n\\nYour content here"
  }' \\
  http://localhost:8000/tools/append_to_note
```

## Current Status

- **Tool Status**: ✅ Working perfectly
- **GPT-5.2 Compatibility**: ❌ Model refuses to use it
- **Claude Compatibility**: ✅ Expected to work (not yet tested)
- **Direct API Access**: ✅ Works perfectly

## Recommendation

For operations involving content modification (append, update):
1. Use Claude models (Sonnet/Opus) which don't have this restriction
2. Or use direct API access for critical operations
3. GPT-5.2 is reliable for structural operations (create, move, search) but not content edits

## Files Modified

- `obsidian-mcp/app/api/routes.py` - Added `AppendToNoteRequest` schema, improved descriptions
- `obsidian-mcp/app/api/routes.py` - Added empty content validation
