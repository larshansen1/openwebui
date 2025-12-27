#!/usr/bin/env python3
"""
Telegram Alert Forwarder
Receives webhooks from Alertmanager and forwards to Telegram
"""

import os
import json
import logging
from flask import Flask, request, jsonify
import requests

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def format_alert(alert):
    """Format alert for Telegram message"""
    status = alert.get('status', 'unknown')
    labels = alert.get('labels', {})
    annotations = alert.get('annotations', {})
    
    # Status emoji
    emoji = '🔥' if status == 'firing' else '✅'
    
    # Severity badge
    severity = labels.get('severity', 'info').upper()
    severity_emoji = {
        'CRITICAL': '🚨',
        'WARNING': '⚠️',
        'INFO': 'ℹ️'
    }.get(severity, 'ℹ️')
    
    # Build message
    message = f"{emoji} {severity_emoji} *Alert {status.upper()}*\n\n"
    message += f"*{labels.get('alertname', 'Unknown Alert')}*\n"
    message += f"Severity: `{severity}`\n"
    message += f"Component: `{labels.get('component', 'unknown')}`\n\n"
    
    # Add summary and description
    if 'summary' in annotations:
        message += f"📝 {annotations['summary']}\n\n"
    if 'description' in annotations:
        message += f"{annotations['description']}\n"
    
    return message


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


@app.route('/alert', methods=['POST'])
def alert():
    """Receive alert from Alertmanager and forward to Telegram"""
    try:
        data = request.json
        
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.error("Telegram credentials not configured")
            return jsonify({'error': 'Telegram not configured'}), 500
        
        # Process each alert
        alerts = data.get('alerts', [])
        for alert in alerts:
            message = format_alert(alert)
            
            # Send to Telegram
            payload = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            response = requests.post(TELEGRAM_API_URL, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Alert sent to Telegram: {alert.get('labels', {}).get('alertname')}")
            else:
                logger.error(f"Failed to send to Telegram: {response.text}")
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Error processing alert: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("⚠️  Telegram credentials not set. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.")
    
    logger.info("🚀 Telegram Alert Forwarder starting...")
    logger.info(f"📱 Telegram Chat ID: {TELEGRAM_CHAT_ID}")
    app.run(host='0.0.0.0', port=8080)
