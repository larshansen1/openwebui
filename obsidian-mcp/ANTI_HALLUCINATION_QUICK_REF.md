# Anti-Hallucination Quick Reference

## Quick Answer: How to Prevent LLM Hallucination

✅ **Implemented** - The proxy mode now includes:

1. **Emphatic tool descriptions** - "MUST call", "CRITICAL", "Do NOT simulate"
2. **Execution IDs** - Every response has unique 8-char ID
3. **Timestamps** - Every response shows when it executed
4. **Clear status markers** - ✅ SUCCESS or ❌ FAILED with explicit text

## How to Verify Tool Was Actually Called

Look for these markers in the response:

```
# ✅ ACTION EXECUTED [a3f9d82c] at 14:32:45
...
---
📋 Execution ID: a3f9d82c | ⏰ Time: 14:32:45
✓ This response is from the actual vault - not simulated.
```

If you DON'T see these markers, the tool wasn't called!

## Common Hallucination Patterns (Now Prevented)

### Pattern 1: Claiming Success Without Calling Tool

**Before Fix:**
```
User: Add tag to note
AI: ✅ Done. I've added the tag.
```
No tool call made! ❌

**After Fix:**
```
User: Add tag to note
AI: [Makes tool call to obsidian]
AI: ✅ Done. I've added the tag. (Execution ID: a3f9d82c)
```
Tool was actually called! ✅

### Pattern 2: Ignoring Failures

**Before Fix:**
```
Tool: ❌ File not found
AI: The note is now updated!
```
AI ignored the error! ❌

**After Fix:**
```
Tool: ❌ EXECUTION FAILED [b7e2f159]
      ⚠️ This tool was called but the operation failed.
      Do NOT tell the user the operation succeeded.

AI: ❌ The operation failed - file not found (ID: b7e2f159)
```
AI must acknowledge failure! ✅

### Pattern 3: Guessing Results

**Before Fix:**
```
User: What tags does the note have?
AI: The note has tags: tech, architecture
```
No tool call - just guessing! ❌

**After Fix:**
```
User: What tags does the note have?
AI: [Makes tool call to get_note]
    Response: ✅ ACTION EXECUTED [c8d2a441]
              Result: {"tags": ["tech", "architecture"]}

AI: The note has tags: tech, architecture (verified via execution c8d2a441)
```
Actual verification! ✅

## If Hallucination Still Occurs

### Step 1: Check Tool Response
Ask the AI: "Show me the execution ID for that operation"

If it can't provide one, it hallucinated!

### Step 2: Ask for Verification
Say: "You didn't actually call the tool. Please call it now."

The new emphatic descriptions will force the call.

### Step 3: Report the Issue
If hallucination persists, the LLM may be:
- Not reading tool descriptions carefully
- Overriding the instructions
- Caching old behavior

Try: "CRITICAL: You must call the obsidian tool to modify the vault. Do not simulate results."

## System Prompt Recommendations

If using an LLM client that supports system prompts, add:

```
TOOL USAGE RULES:
1. ALWAYS call MCP tools for vault operations
2. NEVER claim to have modified files without calling tools
3. NEVER simulate or imagine tool responses
4. Execution IDs prove a tool was called - reference them in responses
5. If a tool fails, acknowledge the failure explicitly
6. When you see "✅ ACTION EXECUTED [ID]" - that's proof it happened
7. When you see "❌ EXECUTION FAILED [ID]" - acknowledge the failure
```

## Debugging Checklist

Use this if you suspect hallucination:

```
[ ] Does the response contain an execution ID? (e.g., [a3f9d82c])
[ ] Does it have a timestamp? (e.g., at 14:32:45)
[ ] Does it say "This operation was actually performed"?
[ ] Can you ask the AI to reference the execution ID?
[ ] If you ask "did you really call the tool?", does it admit or deflect?
```

If 2+ are NO, hallucination likely occurred.

## Example Good Response

```
# ✅ ACTION EXECUTED [a3f9d82c] at 14:32:45

**Action:** update_note
**Bundle:** core
**Status:** SUCCESS - This operation was actually performed

**File Path:** note.md
**Operation:** Completed successfully

💡 To verify this change, you can:
   - Call obsidian(action='get_note', args={'title': '...'}) to check metadata
   - Call obsidian(action='read_note_content', args={'title': '...'}) to read content

---
📋 Execution ID: a3f9d82c | ⏰ Time: 14:32:45
✓ This response is from the actual vault - not simulated.
```

## Example Bad Response (Old Format)

```
The note has been updated with the tag.
```

No execution ID? No timestamp? Not from the actual vault!

## Why This Works

1. **Execution IDs are unforgeable** - LLM can't make up valid UUIDs that match vault state
2. **Timestamps are current** - LLM can't guess the exact time
3. **Explicit language prevents weaseling** - "was actually performed" vs "would be updated"
4. **Failure messages are emphatic** - Hard to ignore "Do NOT tell user it succeeded"

## Summary

The anti-hallucination system works by making it:
- **Obvious** when tools should be called (emphatic descriptions)
- **Impossible** to fake responses (execution IDs + timestamps)
- **Clear** when operations succeed or fail (explicit status)
- **Verifiable** by users (reference execution IDs)

Result: LLMs are forced to call tools and report results truthfully.
