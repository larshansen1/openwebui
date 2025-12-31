# Fixing LLM Tool Hallucination Issue

## Problem

LLMs (like GPT-4, GPT-5.2, Claude, etc.) sometimes **claim** to have called MCP tools without actually making the tool call. They hallucinate the tool execution and response instead of using the real tool.

### Example of the Problem
```
User: Add the architecture tag to the note
AI: ✅ Done. I've added the architecture tag to the note.
    [No actual tool call made]

User: Show me the tags
AI: The note has: tech, architecture
    [Still no tool call - just guessing]

User: You didn't actually do it. Use the tool.
AI: You're right - I have now actually updated the note.
    [Finally makes the tool call]
```

## Root Causes

1. **Weak tool descriptions** - Don't emphasize that tool MUST be called
2. **Ambiguous responses** - LLM can imagine what response would look like
3. **No verification markers** - Nothing proves the tool was actually executed
4. **Model laziness** - Models try to save tokens by avoiding tool calls
5. **Overconfidence** - Model thinks it knows what would happen without calling

## Solutions

### Fix 1: Strengthen Tool Descriptions

**Current** (weak):
```python
Tool(
    name="obsidian",
    description="Execute an Obsidian vault action. Use obsidian_lookup first to discover available actions and required fields.",
    ...
)
```

**Fixed** (emphatic):
```python
Tool(
    name="obsidian",
    description="""EXECUTE an Obsidian vault operation. You MUST actually call this tool - do NOT simulate or imagine the result.

CRITICAL: Always call this tool to perform vault operations. Never claim to have updated, created, or modified notes without calling this tool.

Use obsidian_lookup first to discover available actions and required fields.""",
    ...
)
```

### Fix 2: Add Verification Markers to Responses

Modify `app/mcp/proxy.py` - `ProxyToolFormatter.format_execution_result()`:

**Add timestamp and execution ID:**

```python
import time
import uuid

@staticmethod
def format_execution_result(result: Dict[str, Any]) -> str:
    """Format execution result with verification markers"""

    # Add execution metadata for verification
    execution_id = str(uuid.uuid4())[:8]
    timestamp = time.strftime("%H:%M:%S")

    if not result.get('success', False):
        output = f"# ❌ EXECUTION FAILED [{execution_id}] at {timestamp}\n\n"
        output += f"**Action:** {result.get('action', 'unknown')}\n"
        output += f"**Bundle:** {result.get('bundle', 'unknown')}\n"
        output += f"**Error:** {result.get('error', 'Unknown error')}\n"
        output += f"\n⚠️ The tool was called but the operation failed. You must handle this error.\n"
        return output

    output = f"# ✅ ACTION EXECUTED [{execution_id}] at {timestamp}\n\n"
    output += f"**Action:** {result['action']}\n"
    output += f"**Bundle:** {result['bundle']}\n"
    output += f"**Status:** SUCCESS - This operation was actually performed\n\n"

    # Format result data
    action_result = result.get('result', {})

    if isinstance(action_result, dict):
        # Special formatting for common result types
        if 'count' in action_result and 'results' in action_result:
            output += f"**Found:** {action_result['count']} results\n\n"

        elif 'count' in action_result and 'notes' in action_result:
            output += f"**Found:** {action_result['count']} notes\n\n"

        elif 'content' in action_result:
            output += "**Content:**\n\n"
            output += action_result['content']

        elif 'path' in action_result:
            output += f"**File Path:** {action_result['path']}\n"
            output += f"**Operation:** Completed successfully\n"

        else:
            output += "**Result:**\n\n"
            output += json.dumps(action_result, indent=2)
    else:
        output += f"**Result:** {action_result}\n"

    output += f"\n---\n"
    output += f"Execution ID: {execution_id} | Time: {timestamp}\n"
    output += f"This response is from the actual vault - not simulated.\n"

    return output
```

### Fix 3: Update Tool Descriptions in server_proxy.py

```python
@self.app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available proxy tools"""
    return [
        Tool(
            name="obsidian_lookup",
            description="""Discover what Obsidian action to use for a task. ALWAYS call this tool when you need to find the right action - do NOT guess action names.

Returns: Action name, required fields, optional fields, limits, and confidence score.

Example: obsidian_lookup(intent="add tag to note")""",
            inputSchema={
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "description": "What you want to do (e.g., 'search for notes about AI', 'add tags to note', 'get backlinks')"
                    },
                    "note_hint": {
                        "type": "string",
                        "description": "Optional note title or path hint for context"
                    }
                },
                "required": ["intent"]
            }
        ),
        Tool(
            name="obsidian",
            description="""EXECUTE an Obsidian vault operation. You MUST actually call this tool to perform any vault modification.

⚠️ CRITICAL: Never claim to have created, updated, deleted, or modified notes without calling this tool.
⚠️ Do NOT simulate or imagine results - always make the actual tool call.

The tool returns a verification ID and timestamp proving execution occurred.

Use obsidian_lookup first if you don't know what action to use.

Example: obsidian(action="update_note", args={"file_path": "note.md", "content": "..."})""",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action name to execute (use obsidian_lookup to discover available actions)"
                    },
                    "args": {
                        "type": "object",
                        "description": "Action arguments - structure depends on action (use obsidian_lookup to see required/optional fields)"
                    }
                },
                "required": ["action", "args"]
            }
        ),
        Tool(
            name="obsidian_help",
            description="""Get documentation about Obsidian MCP capabilities. Call this when you need to understand available operations.

Topics: overview, core, search, read, write, templates, graph, admin

Example: obsidian_help(topic="core", verbosity="short")""",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "enum": ["overview", "core", "search", "read", "write", "templates", "graph", "admin"],
                        "description": "Help topic (omit for overview)"
                    },
                    "verbosity": {
                        "type": "string",
                        "enum": ["short", "normal"],
                        "description": "Detail level (default: short)"
                    }
                }
            }
        )
    ]
```

### Fix 4: Add Response Validation Hints

Modify `format_execution_result` to include hints that help the model verify:

```python
# At the end of successful operations:
if 'path' in action_result:
    output += f"\n💡 To verify this change, you can:\n"
    output += f"   - Call obsidian(action='get_note', args={{'title': '...'}}) to check metadata\n"
    output += f"   - Call obsidian(action='read_note_content', args={{'title': '...'}}) to read content\n"
```

### Fix 5: Error Messages That Prevent Hallucination

```python
if not result.get('success', False):
    output = f"# ❌ OPERATION FAILED\n\n"
    output += f"**You attempted:** {result.get('action', 'unknown')}\n"
    output += f"**Error:** {result.get('error', 'Unknown error')}\n\n"
    output += f"⚠️ IMPORTANT: This tool was called but failed.\n"
    output += f"Do NOT tell the user the operation succeeded.\n"
    output += f"Do NOT retry without fixing the error first.\n\n"
    output += f"**Next steps:**\n"
    output += f"1. Read the error message carefully\n"
    output += f"2. Fix the issue (e.g., use correct field names, check file exists)\n"
    output += f"3. Try again with corrected parameters\n"
    return output
```

## Implementation Plan

1. **Update tool descriptions** in `app/mcp/server_proxy.py`
   - Make them emphatic about requiring actual calls
   - Add warnings against simulation
   - Include examples

2. **Add verification markers** in `app/mcp/proxy.py`
   - Import `uuid` and `time`
   - Add execution ID and timestamp to all responses
   - Include explicit "this was actually executed" messages

3. **Enhance error messages** in `app/mcp/proxy.py`
   - Make failures unmistakable
   - Add explicit instructions not to claim success
   - Provide clear next steps

4. **Test with different LLMs**
   - Test with GPT-4, Claude, etc.
   - Verify they actually call tools
   - Check they don't hallucinate responses

## Testing

### Before Fix - LLM Hallucinates:
```
User: Add tag "architecture" to note "multi-tenancy.md"
AI: ✅ Done. I've added the architecture tag.
    [No tool call made - HALLUCINATION]
```

### After Fix - LLM Must Call Tool:
```
User: Add tag "architecture" to note "multi-tenancy.md"
AI: [Calls obsidian_lookup(intent="add tag to note")]
    Response: action="update_note", required_fields=["file_path"], ...

    [Calls obsidian(action="update_note", args={...})]
    Response: ✅ ACTION EXECUTED [a3f9d82c] at 14:32:45
              Action: update_note
              Status: SUCCESS - This operation was actually performed
              File Path: multi-tenancy.md
              ---
              Execution ID: a3f9d82c | Time: 14:32:45
              This response is from the actual vault - not simulated.

AI: ✅ Done. I've added the architecture tag to the note.
    The operation was verified with execution ID a3f9d82c.
```

## Additional Recommendations

### 1. System Prompt Guidance

If your LLM client supports system prompts, add:

```
CRITICAL TOOL USAGE RULES:
1. ALWAYS call MCP tools to perform vault operations
2. NEVER claim to have modified files without calling tools
3. NEVER simulate or imagine tool responses
4. When you see execution IDs and timestamps in responses, those prove the tool was actually called
5. If a tool call fails, acknowledge the failure - don't pretend it succeeded
```

### 2. Response Format Enforcement

Consider adding a check in your LLM client that:
- Detects when LLM claims success without tool call
- Automatically prompts: "You didn't actually call the tool. Please call it now."

### 3. Logging

Add logging to track hallucinations:
```python
# In your LLM client
if "✅" in response and not tool_call_detected:
    logger.warning("Possible hallucination detected - claimed success without tool call")
```

## Files to Modify

1. `obsidian-mcp/app/mcp/server_proxy.py` - Update tool descriptions
2. `obsidian-mcp/app/mcp/proxy.py` - Add verification markers to formatters
3. Your LLM client configuration - Add system prompt rules (if applicable)

## Summary

The key insight is that **LLMs need explicit, emphatic instructions** and **verification markers** to prevent hallucination:

- ⚠️ Use strong language: "MUST", "CRITICAL", "NEVER"
- ✅ Add proof: execution IDs, timestamps
- 🔍 Make success unmistakable: emojis, explicit status
- ❌ Make failures obvious: can't be misinterpreted
- 💡 Provide verification hints: "to check, call X"

This transforms the tools from "nice to call" to "must call to prove work was done".
