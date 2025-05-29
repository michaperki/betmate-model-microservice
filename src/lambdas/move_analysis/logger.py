import logging
import sys
import os
from pythonjsonlogger import jsonlogger

# Global logger instance
_logger = None

def get_logger():
    """Get or create structured logger for move-analysis service."""
    global _logger
    
    if _logger is None:
        _logger = logging.getLogger('move-analysis')
        _logger.setLevel(logging.DEBUG if os.environ.get('NODE_ENV') == 'development' else logging.INFO)
        
        # Remove existing handlers
        _logger.handlers.clear()
        
        # Create console handler with JSON formatter
        handler = logging.StreamHandler(sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
            rename_fields={
                'asctime': 'ts',
                'levelname': 'level', 
                'name': 'service'
            }
        )
        
        handler.setFormatter(formatter)
        _logger.addHandler(handler)
        _logger.propagate = False
    
    return _logger

def log_event(level: str, event: str, trace_id: str = None, **context):
    """Log a structured event."""
    logger = get_logger()
    
    log_data = {
        'event': event,
        'env': os.environ.get('NODE_ENV', 'development')
    }
    
    if trace_id:
        log_data['trace_id'] = trace_id
        
    log_data.update(context)
    
    # Only show debug logs in development
    if level == 'debug' and os.environ.get('NODE_ENV') == 'production':
        return
        
    getattr(logger, level.lower())(None, extra=log_data)