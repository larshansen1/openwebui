# MCP Tools Troubleshooting Guide

## Problem: AI Models Say "I Don't See Any Tools"

Even though Open WebUI shows "Available Tools: Obsidian Vault" in the UI, some AI models claim they can't see or access the tools.

## Root Cause

This is **NOT a configuration issue** with your MCP server. Your infrastructure is working correctly:

✅ MCP server is running and healthy
✅ OpenAPI spec is valid and accessible
✅ Authentication is working
✅ Tools can be called successfully
✅ TOOL_SERVER_CONNECTIONS is configured correctly

**The issue is in Open WebUI's AI provider integration layer.** Open WebUI must:
1. Fetch your OpenAPI spec ✅ (working)
2. Convert it to the AI provider's tool format ⚠️ (unreliable)
3. Include tools in each API request ⚠️ (unreliable)

Step 2-3 fail silently for some AI providers/models.

## Solutions (In Order of Effectiveness)

### 1. **Use Claude Models** (Most Reliable)

Claude has the best tool support in Open WebUI:
- Claude Sonnet 4.5 ✅ (recommended)
- Claude Opus 4.5 ✅
- Claude Haiku 4 ✅

Why: Anthropic's Claude API has excellent function calling support, and Open WebUI's integration is most mature with Claude.

### 2. **Manually Enable Tools Per Chat**

In some Open WebUI versions, tools must be explicitly enabled:

1. Start a new chat
2. Look for "Tools" button/icon near the message input
3. Click and select "Obsidian Vault"
4. Tools should now be available in that chat

### 3. **Verify Model Supports Function Calling**

Not all models support tools. Check:

| Model | Tool Support | Notes |
|-------|--------------|-------|
| Claude Sonnet/Opus/Haiku | ✅ Excellent | Best choice |
| GPT-4, GPT-4 Turbo | ✅ Good | Native OpenAI API works best |
| GPT-5.2 via OpenRouter | ⚠️ Variable | May not pass tools properly |
| Llama models | ⚠️ Limited | Most don't support function calling |
| Local models | ❌ Rarely | Check model card |

**Action**: If using GPT-5.2 via OpenRouter, try switching to:
- Native OpenAI API (not through OpenRouter)
- Claude via Anthropic API
- GPT-4 Turbo

### 4. **Check Open WebUI Admin Settings**

As an admin:

1. Go to **Admin Panel** → **Settings** → **Tools**
2. Verify "Enable Tool Calling" is ON
3. Check if tools require admin approval (disable for testing)
4. Ensure your user has permission to use tools

### 5. **Update Open WebUI**

Current version: **0.6.36**

Tool support improves with each release. Check for updates:

```bash
# Pull latest Open WebUI
docker compose pull openwebui

# Restart
docker compose up -d openwebui
```

### 6. **Debug What's Sent to AI Provider**

Monitor Open WebUI logs during a chat to see if tools are included:

```bash
./scripts/debug-ai-provider-tools.sh
```

Then ask the AI a question and watch for:
- `"tools":` in the API request (good sign)
- `"functions":` in the API request (good sign)
- No tool-related fields (bad sign - tools not being sent)

### 7. **Test with Simple OpenAI-Style API Call**

Verify the AI provider itself supports tools:

```bash
# Test if OpenRouter passes tools correctly
curl -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer YOUR_OPENROUTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-5.2",
    "messages": [{"role": "user", "content": "What tools do you see?"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "test_tool",
        "description": "A test tool",
        "parameters": {"type": "object", "properties": {}}
      }
    }]
  }'
```

If the model responds without mentioning tools, **the provider doesn't support tools for that model**.

## Verification Checklist

Run the test script to verify your infrastructure:

```bash
./scripts/test-tool-integration.sh
```

All checks should pass:
- ✅ OpenAPI spec is valid
- ✅ Tool authentication working
- ✅ Open WebUI can access MCP server
- ✅ Tool execution successful
- ✅ TOOL_SERVER_CONNECTIONS configured

If all pass but AI still can't see tools → **it's the AI provider integration issue**.

## Recommended Workflow

1. **Switch to Claude Sonnet 4.5** (most reliable)
2. **Start a new chat**
3. **Manually select Obsidian Vault tool** if there's a tools selector
4. **Ask a test question**: "What Obsidian vault tools do you have available?"

If Claude can see and use the tools, your setup is perfect—the issue was just the GPT-5.2/OpenRouter combination.

## Why This Happens (Technical Details)

Open WebUI needs to translate your OpenAPI spec to each provider's tool format:

**Your OpenAPI → OpenAI Format:**
```json
{
  "tools": [{
    "type": "function",
    "function": {
      "name": "create_note",
      "parameters": { /* JSON Schema */ }
    }
  }]
}
```

**Your OpenAPI → Anthropic Format:**
```json
{
  "tools": [{
    "name": "create_note",
    "input_schema": { /* JSON Schema */ }
  }]
}
```

This translation can fail if:
- The provider's API structure changes
- Open WebUI's conversion code has bugs
- The model doesn't support tools at all

## Still Not Working?

If you've tried everything:

1. Check Open WebUI GitHub issues: https://github.com/open-webui/open-webui/issues
2. Search for your specific model + "tools" or "function calling"
3. Consider using Claude directly via API (bypass Open WebUI)
4. File a bug report with Open WebUI (include model name, version, logs)

## Quick Reference: Test Commands

```bash
# Test MCP infrastructure
./scripts/test-tool-integration.sh

# Monitor tool usage in real-time
./scripts/debug-ai-provider-tools.sh

# Verify MCP config
./scripts/verify-mcp-config.sh

# Check Open WebUI logs
docker compose logs openwebui --tail=100 | grep -i tool
```
