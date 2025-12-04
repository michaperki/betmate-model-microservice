import logging
import os
import sys
from pythonjsonlogger import jsonlogger

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

def setup_logger(service_name: str) -> logging.Logger:
    """Setup structured JSON logging for microservice components."""
    
    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(get_configured_level())
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Create JSON formatter with ISO8601 timestamp format
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
        rename_fields={
            'asctime': 'ts',
            'levelname': 'level',
            'name': 'service'
        },
        datefmt='%Y-%m-%dT%H:%M:%S.000Z'
    )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger

def log_event(logger: logging.Logger, level: str, event: str, trace_id: str = None, **context):
    """Log a structured event with optional trace_id and context."""
    
    log_data = {
        'event': event,
        'env': os.environ.get('NODE_ENV', 'development')
    }
    
    if trace_id:
        log_data['trace_id'] = trace_id
    
    # Add any additional context
    log_data.update(context)
    
    getattr(logger, level.lower())(None, extra=log_data)
