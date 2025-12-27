#!/bin/bash

set -e

echo "Initializing monitoring data directories..."

# Ensure we're in the project directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Create directories if they don't exist
mkdir -p grafana_data prometheus_data alertmanager_data

# Set correct ownership
# Grafana runs as UID 472
# Prometheus and Alertmanager run as UID 65534 (nobody)
echo "Setting permissions for Grafana (UID 472)..."
sudo chown -R 472:472 grafana_data

echo "Setting permissions for Prometheus (UID 65534)..."
sudo chown -R 65534:65534 prometheus_data

echo "Setting permissions for Alertmanager (UID 65534)..."
sudo chown -R 65534:65534 alertmanager_data

echo ""
echo "✅ Monitoring directories initialized successfully"
echo ""
echo "Directory permissions:"
ls -ld grafana_data prometheus_data alertmanager_data

echo ""
echo "You can now start the monitoring services with:"
echo "  docker compose up -d"
