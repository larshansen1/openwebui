# Open WebUI Monitoring Stack

Production monitoring with OpenTelemetry, Prometheus, Grafana, and Telegram alerts.

## Quick Start

### 1. Configure Environment Variables

Add to your `.env` file:

```bash
# Required for Telegram alerts
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Required for Grafana access
GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 24)
```

### 2. Deploy Monitoring Stack

```bash
# Build and start all monitoring services
docker compose up -d

# Check service health
docker compose ps | grep -E "otel|prometheus|grafana|alertmanager|telegram"
```

### 3. Access Grafana

Via SSH tunnel (localhost only):
```bash
ssh -L 3001:localhost:3001 user@prod-server
```

Then open: http://localhost:3001
- Username: `admin`
- Password: Value from `GRAFANA_ADMIN_PASSWORD` in .env

## Architecture

```
OpenWebUI → OpenTelemetry Collector → Prometheus → Grafana
                                            ↓
                                     Alertmanager → Telegram Forwarder → Telegram
```

## What's Monitored

### 1. Request Latency
- **Metric:** HTTP request duration (p50, p95, p99)
- **Alert:** p95 > 5 seconds (warning), > 10 seconds (critical)
- **Dashboard:** "Request Latency" panel

### 2. API Error Rate
- **Metric:** HTTP 5xx errors / total requests
- **Alert:** Error rate > 1% (warning), > 5% (critical)
- **Dashboard:** "API Error Rate" panel

### 3. MCP Tool Failures
- **Metric:** Failed MCP tool calls (Brave Search, Time, Fetch)
- **Alert:** Failure rate > 10%
- **Dashboard:** "MCP Tool Status" panel

## Alert Routing

All alerts go to Telegram via the configured bot:
- **Warning alerts:** Grouped, sent after 30s delay
- **Critical alerts:** Sent immediately
- **Resolved alerts:** Confirmation sent when issue clears

## Services

| Service | Port | Purpose |
|---------|------|---------|
| otel-collector | 4317 | Receives metrics/traces from OpenWebUI |
| prometheus | 9090 | Stores metrics, evaluates alerts |
| grafana | 3001 | Visualization dashboards |
| alertmanager | 9093 | Routes alerts to Telegram |
| telegram-forwarder | 8080 | Sends alerts to Telegram |

## Troubleshooting

### Metrics not appearing in Grafana

1. Check OpenTelemetry is enabled in OpenWebUI:
```bash
docker exec openwebui env | grep ENABLE_OTEL
```

2. Verify otel-collector is receiving metrics:
```bash
docker logs openwebui-otel-collector --tail 50
```

3. Check Prometheus is scraping otel-collector:
```bash
curl http://localhost:9090/api/v1/targets | jq
```

### Telegram alerts not sending

1. Verify credentials are set:
```bash
docker exec openwebui-telegram-forwarder env | grep TELEGRAM
```

2. Check telegram-forwarder logs:
```bash
docker logs openwebui-telegram-forwarder --tail 50
```

3. Test Telegram bot manually:
```bash
curl -X POST \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_CHAT_ID}" \
  -d "text=Test from Open WebUI monitoring"
```

### High memory usage

Prometheus data retention is set to 15 days. To reduce:
```yaml
# In docker-compose.yml, prometheus service command:
- '--storage.tsdb.retention.time=7d'  # Change from 15d to 7d
```

## Data Persistence

Monitoring data is stored in:
- `./prometheus_data` - Metrics (15 days retention)
- `./grafana_data` - Dashboards and settings
- `./alertmanager_data` - Alert state

**Note:** These directories are excluded from git via `.gitignore`.

## Maintenance

### Validate configurations before deploy

```bash
# Check Prometheus config
docker run --rm -v $(pwd)/monitoring:/etc/prometheus \
  prom/prometheus:latest \
  promtool check config /etc/prometheus/prometheus.yml

# Check alert rules
docker run --rm -v $(pwd)/monitoring:/etc/prometheus \
  prom/prometheus:latest \
  promtool check rules /etc/prometheus/alerts/*.yml
```

### View current alerts

```bash
curl http://localhost:9090/api/v1/alerts | jq
```

### Silence an alert

Access Alertmanager UI: http://localhost:9093 (via SSH tunnel)

## Cost Tracking (Future)

Cost tracking for OpenRouter API usage will be added in a future update.
Planned implementation: Log parser sidecar that tracks model API calls.

## Rollback

To disable monitoring without affecting Open WebUI:

```bash
# Stop monitoring services
docker compose stop otel-collector prometheus grafana alertmanager telegram-forwarder

# Remove OTEL env vars from docker-compose.yml (openwebui service)
# Then restart:
docker compose restart openwebui
```
