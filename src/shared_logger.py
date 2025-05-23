import logging
import os
import sys
from pythonjsonlogger import jsonlogger

def setup_logger(service_name: str) -> logging.Logger:
    """Setup structured JSON logging for microservice components."""
    
    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.DEBUG if os.environ.get('NODE_ENV') == 'development' else logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Create JSON formatter
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
        rename_fields={
            'asctime': 'ts',
            'levelname': 'level', 
            'name': 'service'
        }
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