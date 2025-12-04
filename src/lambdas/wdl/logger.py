import logging
import sys
import os
from pythonjsonlogger import jsonlogger

# Global logger instance
_logger = None

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

def get_logger():
    """Get or create structured logger for WDL service."""
    global _logger
    
    if _logger is None:
        _logger = logging.getLogger('wdl')
        _logger.setLevel(get_configured_level())
        
        # Remove existing handlers
        _logger.handlers.clear()
        
        # Create console handler with JSON formatter and ISO8601 timestamp format
        handler = logging.StreamHandler(sys.stdout)
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
    
    getattr(logger, level.lower())(None, extra=log_data)
