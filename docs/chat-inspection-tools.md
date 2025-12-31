# OpenWebUI Chat Inspection Tools

Three scripts for inspecting chat state in OpenWebUI, each with different use cases:

## 1. `quick-chat-inspect.sh` ⭐ (Recommended)

**Best for:** Quick inspection of chat state

**Features:**
- Automatically inspects most recent chat (or specify chat ID)
- Clean, summarized output
- Uses database queries + jq for formatting
- Exports full JSON to `/tmp/chat-<id>.json`

**Usage:**
```bash
# Most recent chat
./scripts/quick-chat-inspect.sh

# Specific chat
./scripts/quick-chat-inspect.sh <chat_id>
```

**Output:**
- Title, timestamps, models
- System prompt (truncated)
- Message count by role
- Tool call summary

---

## 2. `inspect-chat-db.sh` (Database Deep Dive)

**Best for:** Detailed SQL-based inspection without authentication

**Features:**
- Direct PostgreSQL queries
- Detailed message breakdown
- Tool call arguments inspection
- No auth token needed

**Usage:**
```bash
# Most recent chat
./scripts/inspect-chat-db.sh

# Specific chat
./scripts/inspect-chat-db.sh <chat_id>
```

**Output:**
- Chat metadata (created, updated, user, pinned, archived)
- Models and system prompt
- Message summary (counts by role, tool usage)
- Full message list with content previews
- Detailed tool calls with arguments
- Full JSON export to `/tmp/chat-db-<id>.json`

---

## 3. `inspect-chat.sh` (REST API)

**Best for:** Programmatic access via OpenWebUI API

**Features:**
- Uses OpenWebUI REST API
- Good for automation/scripts
- Requires authentication token

**Usage:**
```bash
./scripts/inspect-chat.sh
# Follow prompts to enter auth token from browser

# Get token from browser console:
localStorage.getItem('token')
```

**Output:**
- Chat list or specific chat details
- Message structure with tool calls
- JSON export

---

## Comparison

| Feature | quick-chat-inspect | inspect-chat-db | inspect-chat (API) |
|---------|-------------------|-----------------|-------------------|
| **Auth Required** | No | No | Yes (browser token) |
| **Speed** | Fast | Fast | Medium |
| **Detail Level** | Summary | Detailed | Medium |
| **Tool Arguments** | No | Yes | Yes |
| **Best For** | Quick checks | Deep debugging | Automation |

## Example Output

### quick-chat-inspect.sh
```
📊 Most Recent Chat: b98910cf-3910...
✅ Full chat data saved to: /tmp/chat-b98910cf-3910....json

📋 Summary:
===========
Title: 🧰 Available Chat Capabilities
Created: 2025-12-31T09:32:04Z
Updated: 2025-12-31T09:32:20Z
Models: openai/gpt-5.2
System Prompt: When searching Obsidian notes for tags, ALWAYS set searchFrontmatter=true...

Messages: 2

💬 Message Roles:
  [USER] Which tools do you have available?...
  [ASSISTANT] <details type="reasoning" done="true" duration="1">...

🔧 Tool Calls:
  No tool calls found
```

### inspect-chat-db.sh
```
📊 Chat Metadata:
================
id         | title                          | created_at           | user_id
-----------+--------------------------------+----------------------+--------
b98910cf.. | 🧰 Available Chat Capabilities | 2025-12-31 09:32:04 | 235737..

🤖 Models & System Prompt:
==========================
model          | system_prompt
---------------+-------------------------------------
openai/gpt-5.2 | When searching Obsidian notes for...

💬 Messages Summary:
===================
total | user | assistant | with_tools
------+------+-----------+-----------
    2 |    1 |         1 |          0

📝 Message Details:
===================
msg_num | role      | content_preview         | has_tools | timestamp
--------+-----------+-------------------------+-----------+----------
      1 | user      | Which tools do you...   | No        | 2025-12-31
      2 | assistant | <details type="reas...  | No        | 2025-12-31
```

## Tips

1. **Finding Chat IDs**: Both scripts show chat IDs in their output
2. **JSON Inspection**: All tools export full JSON for deep inspection with `jq`
3. **Performance**: Database scripts are faster than API (no HTTP overhead)
4. **Debugging Tool Calls**: Use `inspect-chat-db.sh` to see exact tool arguments

## Common Use Cases

**"What did the AI just do?"**
→ `./scripts/quick-chat-inspect.sh`

**"Why did this tool call fail?"**
→ `./scripts/inspect-chat-db.sh` (shows full arguments)

**"What's in my chat history?"**
→ View exported JSON: `cat /tmp/chat-*.json | jq .chat.messages`

**"Script automation"**
→ Use `inspect-chat.sh` with API token
