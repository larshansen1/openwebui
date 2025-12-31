import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def log_validation_event(
    action: str, 
    event_type: str, 
    details: Dict[str, Any],
    level: str = "warning"
):
    """
    Log a structured validation event for observability.
    
    Args:
        action: The action name (e.g. 'update_note')
        event_type: The type of event (e.g. 'unknown_fields', 'missing_fields')
        details: Dictionary of event details
        level: Log level ('info', 'warning', 'error')
    """
    payload = {
        "event": "validation",
        "action": action,
        "type": event_type,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    
    log_message = json.dumps(payload)
    
    if level == "error":
        logger.error(log_message)
    elif level == "warning":
        logger.warning(log_message)
    else:
        logger.info(log_message)
