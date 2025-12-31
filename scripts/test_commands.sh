#!/bin/bash

# Configuration
API_KEY=$(grep MCP_API_KEY .env | cut -d= -f2)
URL="http://localhost:8001/mcp/execute"

echo "🧪 Testing Obsidian MCP Fixes..."
echo "================================="

# Function to run test
run_test() {
    echo -n "Testing $1... "
    response=$(curl -s -X POST "$URL" \
      -H "Authorization: Bearer $API_KEY" \
      -H "Content-Type: application/json" \
      -d "$2")

    if echo "$response" | grep -q "\"success\":true"; then
        echo "✅ PASS"
    else
        echo "❌ FAIL"
        echo "Response: $response"
    fi
}

# 1. Test Search with Singular 'tag'
run_test "Search with singular 'tag'" \
  '{"action": "search_notes", "args": {"tag": "architecture"}}'

# 2. Test Search with Plural 'tags'
run_test "Search with plural 'tags'" \
  '{"action": "search_notes", "args": {"tags": ["architecture"]}}'

# 3. Test Update Note by Title
echo "Creating test note first..."
curl -s -X POST "$URL" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"action": "create_note", "args": {"title": "Test Note For Updates", "content": "# Test Note\nOriginal content"}}' > /dev/null

run_test "Update note by 'title' (no file_path)" \
  '{"action": "update_note", "args": {"title": "Test Note For Updates", "content": "# Updated\nNew content via title"}}'

# 4. Test Update Note by 'path' alias
run_test "Update note by 'path' alias" \
  '{"action": "update_note", "args": {"path": "Test Note For Updates.md", "content": "# Updated\nNew content via path alias"}}'

# 5. Test Get Note by 'name' alias
run_test "Get note by 'name' alias" \
  '{"action": "get_note", "args": {"name": "Test Note For Updates"}}'

# 6. Test Read Note by 'name' alias
run_test "Read note by 'name' alias" \
  '{"action": "read_note_content", "args": {"name": "Test Note For Updates"}}'

# 7. Test Delete Note by Title
run_test "Delete note by 'title'" \
  '{"action": "delete_note", "args": {"title": "Test Note For Updates"}}'

echo "================================="
echo "Done."
