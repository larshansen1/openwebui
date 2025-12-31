#!/bin/bash
# Quick chat inspector - outputs most recent chat in pretty JSON
# Usage: ./quick-chat-inspect.sh [chat_id]

set -e

sql() {
    docker compose exec -T postgres psql -U openwebui -d openwebui -At -c "$1"
}

if [ -z "$1" ]; then
    # Get most recent chat
    CHAT_ID=$(sql "SELECT id FROM chat ORDER BY updated_at DESC LIMIT 1;")
    echo "📊 Most Recent Chat: $CHAT_ID" >&2
else
    CHAT_ID=$1
    echo "📊 Chat: $CHAT_ID" >&2
fi

# Export to file and display summary
FILE="/tmp/chat-$CHAT_ID.json"

sql "SELECT row_to_json(chat.*) FROM chat WHERE id = '$CHAT_ID';" | jq . > "$FILE"

echo "" >&2
echo "✅ Full chat data saved to: $FILE" >&2
echo "" >&2

# Show summary
echo "📋 Summary:" >&2
echo "===========" >&2
jq -r '
  "Title: \(.title)",
  "Created: \(.created_at | todate)",
  "Updated: \(.updated_at | todate)",
  "Models: \(.chat.models | join(", "))",
  "System Prompt: \(.chat.system // "None" | .[0:80])\(if (.chat.system | length) > 80 then "..." else "" end)",
  "",
  "Messages: \(.chat.messages | length)"
' "$FILE" >&2

echo "" >&2
echo "💬 Message Roles:" >&2
jq -r '.chat.messages[] | "  [\(.role | ascii_upcase)] \(.content[0:70] // "N/A")..."' "$FILE" >&2

echo "" >&2
echo "🔧 Tool Calls:" >&2
jq -r '
  .chat.messages[] |
  select(.tool_calls) |
  "  [\(.id[0:8])] \(.tool_calls | length) tool call(s) - " + (.tool_calls[] | .function.name) | unique | join(", ")
' "$FILE" >&2 || echo "  No tool calls found" >&2

echo "" >&2
echo "📄 View full JSON: cat $FILE | jq ." >&2
