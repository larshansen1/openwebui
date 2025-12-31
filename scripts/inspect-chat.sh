#!/bin/bash
# Inspect OpenWebUI chat state via API
# Usage: ./inspect-chat.sh [chat_id]

set -e

echo "OpenWebUI Chat Inspector"
echo "========================"
echo ""

# Check if we're running
if ! docker ps | grep -q openwebui; then
    echo "❌ OpenWebUI is not running"
    exit 1
fi

# Get auth token from user
echo "To get your auth token:"
echo "1. Open OpenWebUI in browser (http://localhost:3000)"
echo "2. Open DevTools (F12) → Console"
echo "3. Run: localStorage.getItem('token')"
echo "4. Copy the token (without quotes)"
echo ""
read -p "Enter your auth token: " TOKEN

if [ -z "$TOKEN" ]; then
    echo "❌ Token is required"
    exit 1
fi

BASE_URL="http://localhost:3000/api/v1"

# Function to make authenticated API calls
api_call() {
    curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL$1"
}

if [ -z "$1" ]; then
    # List all chats
    echo "📋 Listing all chats..."
    echo ""
    api_call "/chats" | jq -r '.[] | "ID: \(.id)\nTitle: \(.title)\nCreated: \(.created_at)\n---"'
    echo ""
    echo "💡 To inspect a specific chat, run: $0 <chat_id>"
else
    CHAT_ID=$1
    echo "🔍 Inspecting chat: $CHAT_ID"
    echo ""
    
    # Get chat metadata
    echo "📊 Chat Metadata:"
    echo "================"
    api_call "/chats/$CHAT_ID" | jq '{
        id,
        title,
        created_at,
        updated_at,
        model: .chat.model,
        message_count: (.chat.messages | length)
    }'
    echo ""
    
    # Get detailed messages
    echo "💬 Messages (with tool calls):"
    echo "=============================="
    api_call "/chats/$CHAT_ID" | jq -r '
        .chat.messages[] | 
        "[\(.role | ascii_upcase)] \(.created_at // "unknown time")
        
Content: \(.content // "N/A")
        
\(if .tool_calls then "🔧 Tool Calls: \(.tool_calls | length)" else "" end)
\(if .tool_calls then (.tool_calls[] | "  - \(.function.name)(\(.function.arguments | fromjson | to_entries | map("\(.key)=\(.value)") | join(", ")))") else "" end)

---"
    '
    
    echo ""
    echo "💾 Full JSON (saved to /tmp/chat-$CHAT_ID.json):"
    api_call "/chats/$CHAT_ID" | jq . > "/tmp/chat-$CHAT_ID.json"
    echo "Saved to: /tmp/chat-$CHAT_ID.json"
fi
