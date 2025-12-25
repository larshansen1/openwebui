#!/bin/sh
set -e

echo "🔒 MCP Server Secure Startup"
echo "============================="

# Validate required environment variables
if [ -z "$MCP_API_KEY" ]; then
    echo "❌ ERROR: MCP_API_KEY environment variable is required"
    exit 1
fi

if [ ${#MCP_API_KEY} -lt 16 ]; then
    echo "❌ ERROR: MCP_API_KEY must be at least 16 characters for security"
    exit 1
fi

echo "✅ Environment variables validated"

# Generate config with proper JSON parsing and security
python3 -c "
import os
import json
import sys

try:
    # Read template
    print('📖 Reading config template...')
    with open('/app/config/config.template.json', 'r') as f:
        config = json.load(f)

    # Validate structure
    if 'mcpServers' not in config:
        raise ValueError('Invalid config template: missing mcpServers')

    # Safely inject environment variables
    brave_key = os.environ.get('BRAVE_API_KEY', '').strip()

    # Update brave-search config if it exists
    if 'brave-search' in config['mcpServers']:
        if 'env' in config['mcpServers']['brave-search']:
            if brave_key:
                config['mcpServers']['brave-search']['env']['BRAVE_API_KEY'] = brave_key
                print('✅ Brave Search API key configured')
            else:
                print('⚠️  Warning: BRAVE_API_KEY not set, brave-search may fail')

    # Write final config to writable tmp directory
    print('📝 Writing secure config...')
    config_path = '/tmp/config.json'
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    # Set restrictive permissions (readable only by current user)
    os.chmod(config_path, 0o600)

    print('✅ Config generated successfully')
    print('🔒 Permissions set to 600 (owner read/write only)')

except Exception as e:
    print(f'❌ ERROR: Failed to generate config: {e}', file=sys.stderr)
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Config generation failed"
    exit 1
fi

echo "🚀 Starting MCP Server..."
echo ""

# Start mcpo with the generated config in tmp
exec mcpo --port 8000 --api-key "$MCP_API_KEY" --config /tmp/config.json "$@"
