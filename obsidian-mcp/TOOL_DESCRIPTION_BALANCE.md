# Tool Description Balance: Access vs Accuracy

## The Challenge

Tool descriptions must balance two competing needs:

1. **Making LLMs aware they HAVE access** to capabilities
2. **Preventing LLMs from CLAIMING access** without actually calling tools

## The Problem We Solved

### Issue 1: Hallucination (Over-confidence)
**Symptom:** LLM claims to have executed operations without calling tools
```
User: Add tag to note
AI: ✅ Done. I've added the tag.
     [No tool call made!]
```

**Cause:** Tool descriptions didn't emphasize need to actually call tools

### Issue 2: False Denial (Under-confidence)
**Symptom:** LLM claims NOT to have access when it does
```
User: List notes in my vault
AI: I don't have access to your vault.
     [Doesn't realize it has MCP tools!]
```

**Cause:** Tool descriptions didn't emphasize that access IS available

## The Solution: Balanced Descriptions

### Key Principle
**Lead with availability, follow with requirements**

### Structure
```
"YOU HAVE ACCESS to [capability].
Use this tool to [action].
You MUST call this tool [when].
CRITICAL: Never claim [without calling]."
```

### Breakdown

**Part 1: Availability** (Solves false denial)
> "YOU HAVE ACCESS to an Obsidian vault."

**Part 2: Purpose** (Clarifies when to use)
> "Use this tool to EXECUTE vault operations: list notes, search notes, create notes..."

**Part 3: Requirement** (Prevents hallucination)
> "You MUST call this tool to perform any vault operation."

**Part 4: Warning** (Reinforces requirement)
> "CRITICAL: Never claim to have accessed vault content without calling this tool."

## Examples

### obsidian_lookup Tool

**Bad (Causes false denial):**
```
"Discover what action to use for a task."
```
→ LLM thinks: "This is about discovering actions, not about vault access"

**Good (Balanced):**
```
"YOU HAVE ACCESS to an Obsidian vault through MCP tools.
Use this tool to discover what action to use for vault operations
(search, create, update, read notes, etc.).
ALWAYS call this when you need to find the right action."
```
→ LLM thinks: "I have vault access! This tool helps me use it."

### obsidian Tool

**Bad (Causes false denial):**
```
"Execute an Obsidian vault action."
```
→ LLM thinks: "I don't have an Obsidian vault"

**Bad (Causes hallucination):**
```
"Access the vault to list, search, create, update notes."
```
→ LLM thinks: "I can just describe what would happen"

**Good (Balanced):**
```
"YOU HAVE ACCESS to an Obsidian vault.
Use this tool to EXECUTE vault operations: list notes, search notes,
create notes, update notes, read content, manage tags, etc.
You MUST call this tool to perform any vault operation.
CRITICAL: Never claim to have accessed vault content without calling this tool."
```
→ LLM thinks: "I have access! I must use the tool to prove it."

### obsidian_help Tool

**Bad (Ambiguous):**
```
"Get help about Obsidian capabilities."
```
→ LLM thinks: "Generic documentation, not about MY access"

**Good (Clear):**
```
"YOU HAVE ACCESS to an Obsidian vault.
Get documentation about available vault operations and capabilities.
Use this to understand what you can do with the vault."
```
→ LLM thinks: "I have a vault and this tells me what I can do with it"

## Testing Your Balance

### Test 1: Access Awareness
```
User: "List notes in my vault"
Expected: LLM calls obsidian(action='list_notes', args={})
Bad: "I don't have access to your vault"
Good: [Makes tool call] "Here are your notes..."
```

### Test 2: Hallucination Prevention
```
User: "Add tag 'test' to note.md"
Expected: LLM calls obsidian tool, references execution ID
Bad: "✅ Done." [No tool call]
Good: [Makes tool call] "✅ Done (ID: a3f9d82c)"
```

### Test 3: Capability Discovery
```
User: "What can you do with my vault?"
Expected: LLM calls obsidian_help or lists capabilities from descriptions
Bad: "I can't access your vault"
Good: "I have access to your Obsidian vault. I can: list notes, search..."
```

## Checklist for Good Tool Descriptions

- [ ] Starts with "YOU HAVE ACCESS to..."
- [ ] Clearly states what capability is available
- [ ] Lists example operations (search, create, update, etc.)
- [ ] Uses "Use this tool to..." (directive)
- [ ] Includes "MUST call" or "ALWAYS call"
- [ ] Has "CRITICAL: Never claim..." warning
- [ ] Examples in schema descriptions
- [ ] NOT ambiguous about availability
- [ ] NOT so strict it causes false denial
- [ ] NOT so loose it allows hallucination

## Common Mistakes

### ❌ Too Passive
```
"Execute vault actions"
```
Problems:
- Doesn't mention access availability
- LLM may think it doesn't have a vault

### ❌ Too Strict
```
"CRITICAL: MUST call this tool. Never skip calling this tool."
```
Problems:
- Doesn't mention what access it provides
- LLM doesn't know WHEN to use it

### ❌ Too Vague
```
"Work with notes in Obsidian"
```
Problems:
- "Work with" could mean many things
- No emphasis on actual tool calls
- Allows hallucination

### ✅ Just Right
```
"YOU HAVE ACCESS to an Obsidian vault.
Use this tool to EXECUTE vault operations: list, search, create, update notes.
You MUST call this tool to perform any vault operation.
CRITICAL: Never claim to have accessed vault without calling this tool."
```
Benefits:
- Clear about access availability
- Lists concrete operations
- Requires actual tool calls
- Prevents hallucination

## Summary

**The Golden Formula:**

1. **Availability First** → "YOU HAVE ACCESS to X"
2. **Purpose Clear** → "Use this tool to DO Y"
3. **Examples Concrete** → "list, search, create, update"
4. **Requirement Strong** → "You MUST call this tool"
5. **Warning Explicit** → "Never claim without calling"

This balances:
- ✅ Making LLMs aware of capabilities (prevents false denial)
- ✅ Requiring actual tool calls (prevents hallucination)
- ✅ Providing clear usage guidance (when to use)

Result: LLMs know they have access AND know they must prove it by calling tools.
