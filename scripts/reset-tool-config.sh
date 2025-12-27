#!/bin/bash
# Reset Open WebUI tool server connections config
# This forces re-initialization from TOOL_SERVER_CONNECTIONS environment variable

set -e

echo "Resetting tool server connections configuration..."

# Wait for postgres to be ready
until docker exec openwebui-postgres pg_isready -U openwebui > /dev/null 2>&1; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done

# Delete tool server config from database to force re-initialization
docker exec openwebui-postgres psql -U openwebui -d openwebui -c \
  "DELETE FROM config WHERE data::text LIKE '%TOOL_SERVER%' OR data::text LIKE '%tool_server%';" \
  2>/dev/null || true

echo "Tool configuration reset. Restart openwebui container to apply new TOOL_SERVER_CONNECTIONS."
