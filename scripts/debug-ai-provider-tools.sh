#!/bin/bash
# Debug what Open WebUI sends to AI providers

echo "Monitoring Open WebUI → AI Provider communication..."
echo "This will show tool-related API calls"
echo "Press Ctrl+C to stop"
echo ""

# Follow logs and filter for tool-related activity
docker compose logs -f openwebui | grep -E "(tool|function|TOOL|openapi|obsidian)" --color=always
