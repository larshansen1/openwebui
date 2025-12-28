#!/usr/bin/env python3
"""
Telegram Alert Forwarder
Receives webhooks from Alertmanager and forwards to Telegram
"""

import os
import json
import logging
import hmac
import hashlib
from functools import wraps
from flask import Flask, request, jsonify
import requests

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
WEBHOOK_SECRET = os.environ.get('ALERTMANAGER_WEBHOOK_SECRET')  # Optional authentication

# Security limits
MAX_PAYLOAD_SIZE = 1024 * 1024  # 1MB
MAX_ALERTS_PER_REQUEST = 100
MAX_TEXT_LENGTH = 1000

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_PAYLOAD_SIZE


def sanitize_text(text, max_length=MAX_TEXT_LENGTH):
    """Sanitize and truncate text for safe display"""
    if not isinstance(text, str):
        text = str(text)

    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length-3] + '...'

    # Escape special Markdown characters for Telegram
    # Only escape problematic characters, keep basic formatting
    text = text.replace('`', '\\`')
    text = text.replace('\\', '\\\\')

    return text


def verify_webhook_auth(f):
    """Optional webhook authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If webhook secret is configured, verify it
        if WEBHOOK_SECRET:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                logger.warning(f"Unauthorized request from {request.remote_addr}")
                return jsonify({'error': 'Unauthorized'}), 401

            provided_secret = auth_header[7:]  # Remove 'Bearer ' prefix
            if not hmac.compare_digest(provided_secret, WEBHOOK_SECRET):
                logger.warning(f"Invalid webhook secret from {request.remote_addr}")
                return jsonify({'error': 'Invalid credentials'}), 401

        return f(*args, **kwargs)
    return decorated_function


def format_alert(alert):
    """Format alert for Telegram message with sanitization"""
    # Validate alert structure
    if not isinstance(alert, dict):
        logger.warning("Invalid alert structure (not a dict)")
        return None

    status = alert.get('status', 'unknown')
    labels = alert.get('labels') or {}
    annotations = alert.get('annotations') or {}

    # Validate types
    if not isinstance(labels, dict) or not isinstance(annotations, dict):
        logger.warning("Invalid alert labels or annotations")
        return None

    # Status emoji
    emoji = '🔥' if status == 'firing' else '✅'

    # Severity badge
    severity = sanitize_text(labels.get('severity', 'info')).upper()
    severity_emoji = {
        'CRITICAL': '🚨',
        'WARNING': '⚠️',
        'INFO': 'ℹ️'
    }.get(severity, 'ℹ️')

    # Build message with sanitized content
    message = f"{emoji} {severity_emoji} *Alert {status.upper()}*\n\n"
    message += f"*{sanitize_text(labels.get('alertname', 'Unknown Alert'), 100)}*\n"
    message += f"Severity: `{severity}`\n"
    message += f"Component: `{sanitize_text(labels.get('component', 'unknown'), 50)}`\n\n"

    # Add summary and description with sanitization
    if 'summary' in annotations:
        message += f"📝 {sanitize_text(annotations['summary'], 300)}\n\n"
    if 'description' in annotations:
        message += f"{sanitize_text(annotations['description'], 500)}\n"

    return message


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


@app.route('/alert', methods=['POST'])
@verify_webhook_auth
def alert():
    """Receive alert from Alertmanager and forward to Telegram with validation"""
    try:
        # Validate Content-Type
        if not request.is_json:
            logger.warning(f"Invalid Content-Type from {request.remote_addr}")
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        # Check Telegram configuration
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.error("Telegram credentials not configured")
            return jsonify({'error': 'Telegram not configured'}), 500

        # Parse and validate JSON
        data = request.json
        if not isinstance(data, dict):
            logger.warning(f"Invalid JSON structure from {request.remote_addr}")
            return jsonify({'error': 'Invalid JSON structure'}), 400

        # Validate alerts array
        alerts = data.get('alerts', [])
        if not isinstance(alerts, list):
            logger.warning(f"Invalid alerts field from {request.remote_addr}")
            return jsonify({'error': 'alerts must be an array'}), 400

        # Limit number of alerts
        if len(alerts) > MAX_ALERTS_PER_REQUEST:
            logger.warning(f"Too many alerts ({len(alerts)}) from {request.remote_addr}")
            return jsonify({'error': f'Too many alerts (max {MAX_ALERTS_PER_REQUEST})'}), 400

        # Process each alert
        sent_count = 0
        failed_count = 0

        for alert in alerts:
            message = format_alert(alert)

            # Skip invalid alerts
            if message is None:
                failed_count += 1
                continue

            # Send to Telegram
            payload = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }

            try:
                response = requests.post(TELEGRAM_API_URL, json=payload, timeout=10)

                if response.status_code == 200:
                    alertname = alert.get('labels', {}).get('alertname', 'unknown')
                    logger.info(f"Alert sent to Telegram: {alertname}")
                    sent_count += 1
                else:
                    logger.error(f"Telegram API error: {response.status_code}")
                    failed_count += 1
            except requests.exceptions.Timeout:
                logger.error("Telegram API timeout")
                failed_count += 1
            except requests.exceptions.RequestException as e:
                logger.error(f"Telegram API request failed: {e}")
                failed_count += 1

        return jsonify({
            'status': 'ok',
            'sent': sent_count,
            'failed': failed_count
        }), 200

    except Exception as e:
        # Log the full error but don't expose details to client
        logger.error(f"Error processing alert: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("⚠️  Telegram credentials not set. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.")

    logger.info("🚀 Telegram Alert Forwarder starting...")

    # Mask chat ID for security (show first/last 4 chars only)
    if TELEGRAM_CHAT_ID:
        masked_chat_id = f"{TELEGRAM_CHAT_ID[:4]}...{TELEGRAM_CHAT_ID[-4:]}" if len(TELEGRAM_CHAT_ID) > 8 else "****"
        logger.info(f"📱 Telegram Chat ID: {masked_chat_id}")

    # Log if webhook authentication is enabled
    if WEBHOOK_SECRET:
        logger.info("🔒 Webhook authentication: ENABLED")
    else:
        logger.warning("⚠️  Webhook authentication: DISABLED (set ALERTMANAGER_WEBHOOK_SECRET to enable)")

    logger.info(f"📊 Security limits: Max payload={MAX_PAYLOAD_SIZE/1024}KB, Max alerts={MAX_ALERTS_PER_REQUEST}")
    app.run(host='0.0.0.0', port=8080)
