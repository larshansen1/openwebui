#!/bin/bash
# Inspect OpenWebUI chat state via direct database access
# Usage: ./inspect-chat-db.sh [chat_id]

set -e

echo "OpenWebUI Chat Inspector (Database)"
echo "===================================="
echo ""

# Check if postgres is running
if ! docker ps | grep -q openwebui-postgres; then
    echo "❌ PostgreSQL is not running"
    exit 1
fi

# Function to run SQL queries
sql() {
    docker compose exec -T postgres psql -U openwebui -d openwebui -c "$1"
}

if [ -z "$1" ]; then
    # Get most recent chat
    echo "🔎 Finding most recent chat..."
    CHAT_ID=$(sql "SELECT id FROM chat ORDER BY updated_at DESC LIMIT 1;" | sed -n 3p | xargs)
    
    if [ -z "$CHAT_ID" ]; then
        echo "❌ No chats found in database"
        exit 1
    fi
    
    echo "✅ Found most recent chat: $CHAT_ID"
    echo ""
else
    CHAT_ID=$1
fi

echo "🔍 Inspecting chat: $CHAT_ID"
echo ""
    
# Get chat info
echo "📊 Chat Metadata:"
echo "================"
sql "
    SELECT 
        id,
        title,
        to_timestamp(created_at) as created_at,
        to_timestamp(updated_at) as updated_at,
        user_id,
        pinned,
        archived
    FROM chat 
    WHERE id = '$CHAT_ID';
"

echo ""
echo "🤖 Models & System Prompt:"
echo "=========================="
sql "
    SELECT 
        json_array_elements_text((chat->'models')::json) as model,
        LEFT(COALESCE((chat->>'system'), 'None'), 100) as system_prompt
    FROM chat 
    WHERE id = '$CHAT_ID'
    LIMIT 1;
"

echo ""
echo "💬 Messages Summary:"
echo "==================="
sql "
    WITH messages AS (
        SELECT json_array_elements((chat->'messages')::json) as msg
        FROM chat
        WHERE id = '$CHAT_ID'
    )
    SELECT 
        COUNT(*) as total_messages,
        COUNT(CASE WHEN msg->>'role' = 'user' THEN 1 END) as user_messages,
        COUNT(CASE WHEN msg->>'role' = 'assistant' THEN 1 END) as assistant_messages,
        COUNT(CASE WHEN msg->'tool_calls' IS NOT NULL THEN 1 END) as messages_with_tools
    FROM messages;
"

echo ""
echo "📝 Message Details:"
echo "==================="
sql "
    SELECT 
        ROW_NUMBER() OVER (ORDER BY (msg->>'timestamp')::bigint) as msg_num,
        msg->>'role' as role,
        LEFT(msg->>'content', 80) as content_preview,
        CASE 
            WHEN msg->'tool_calls' IS NOT NULL THEN 
                'Yes (' || json_array_length((msg->'tool_calls')::json) || ')'
            ELSE 'No'
        END as has_tools,
        to_timestamp((msg->>'timestamp')::bigint) as timestamp
    FROM chat,
        json_array_elements((chat->'messages')::json) as msg
    WHERE id = '$CHAT_ID'
    ORDER BY (msg->>'timestamp')::bigint;
"

echo ""
echo "🔧 Tool Calls (detailed):"
echo "========================"
sql "
    SELECT 
        msg->>'id' as message_id,
        msg->>'role' as role,
        tool_call->'function'->>'name' as tool_name,
        tool_call->'function'->'arguments' as arguments,
        to_timestamp((msg->>'timestamp')::bigint) as timestamp
    FROM chat,
        json_array_elements((chat->'messages')::json) as msg,
        json_array_elements((msg->'tool_calls')::json) as tool_call
    WHERE id = '$CHAT_ID'
    ORDER BY (msg->>'timestamp')::bigint;
" || echo "  No tool calls in this chat"

echo ""
echo "💾 Full chat JSON exported"
sql "
    SELECT jsonb_pretty(row_to_json(chat.*)::jsonb)
    FROM chat 
    WHERE id = '$CHAT_ID';
" > "/tmp/chat-db-$CHAT_ID.json"

echo "Saved to: /tmp/chat-db-$CHAT_ID.json"
echo ""
echo "📄 View with: cat /tmp/chat-db-$CHAT_ID.json | jq ."

