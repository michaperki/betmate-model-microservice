import logging
import sys
import os
import json
import requests
from datetime import datetime
from pythonjsonlogger import jsonlogger

# Global logger instance
_logger = None
_axiom_enabled = False
_axiom_client = None

LEVEL_MAP = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'WARN': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}

def get_configured_level() -> int:
    level_name = os.environ.get('LOG_LEVEL', 'WARNING').strip().upper()
    return LEVEL_MAP.get(level_name, logging.WARNING)

class AxiomHandler(logging.Handler):
    """Custom logging handler that sends logs to Axiom"""
    
    def __init__(self, token, dataset="betmate-logs"):
        super().__init__()
        self.token = token
        self.dataset = dataset
        self.endpoint = f"https://api.axiom.co/v1/datasets/{dataset}/ingest"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
    def emit(self, record):
        try:
            log_entry = self.format(record)
            
            # Format as expected by Axiom
            payload = json.loads(log_entry)
            
            # Batch as list of events
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json=[payload]
            )
            
            if response.status_code >= 400:
                fallback = json.dumps({
                    "error": "Failed to send to Axiom",
                    "status_code": response.status_code,
                    "details": response.text,
                    "original_log": payload
                })
                print(fallback, file=sys.stderr)
                
        except Exception as e:
            fallback = json.dumps({
                "error": "Exception sending log to Axiom",
                "details": str(e),
                "original_log": record.__dict__
            })
            print(fallback, file=sys.stderr)

def get_logger(service_name="microservice"):
    """Get or create structured logger with Axiom integration."""
    global _logger, _axiom_enabled
    
    if _logger is None:
        _logger = logging.getLogger(service_name)
        _logger.setLevel(get_configured_level())
        
        # Remove existing handlers
        _logger.handlers.clear()
        
        # Create formatter with fields that match backend format and ISO8601 timestamp
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
            rename_fields={
                'asctime': 'ts',
                'levelname': 'level',
                'name': 'service'
            },
            datefmt='%Y-%m-%dT%H:%M:%S.000Z'
        )
        
        # Always add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        _logger.addHandler(console_handler)
        
        # Add Axiom handler if API key is available and in production or explicitly enabled
        axiom_api_key = os.environ.get('AXIOM_API_KEY')
        env = os.environ.get('NODE_ENV', 'development')
        axiom_enabled = os.environ.get('ENABLE_AXIOM_LOGGING', 'false').lower() == 'true'

        if axiom_api_key and (env == 'production' or axiom_enabled):
            try:
                axiom_handler = AxiomHandler(token=axiom_api_key)
                axiom_handler.setFormatter(formatter)
                _logger.addHandler(axiom_handler)
                _axiom_enabled = True
                print(f"Axiom logging initialized for service: {service_name} in {env} environment")
            except Exception as e:
                print(f"Failed to initialize Axiom logging: {str(e)}")
        elif not axiom_api_key:
            print("Axiom logging disabled: No AXIOM_API_KEY found in environment")
        else:
            print(f"Axiom logging disabled in {env} environment (set ENABLE_AXIOM_LOGGING=true to override)")
        
        _logger.propagate = False
    
    return _logger

def log_event(level: str, event: str, trace_id: str = None, **context):
    """Log a structured event with Axiom compatibility."""
    logger = get_logger()
    
    # Create a structured log entry similar to backend format
    # Note: We don't need to manually set the timestamp as the formatter handles it
    log_data = {
        'event': event,
        'env': os.environ.get('NODE_ENV', 'development')
    }
    
    if trace_id:
        log_data['trace_id'] = trace_id
        
    # Add all context data
    log_data.update(context)
    
    # Use the appropriate log level method
    getattr(logger, level.lower())(None, extra=log_data)

def generate_trace_id():
    """Generate a random trace ID for request correlation."""
    import random
    import string
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
