#!/usr/bin/env python3
"""
Simple test script that outputs log messages with the normalized timestamp format
"""
import logging
import sys
from pythonjsonlogger import jsonlogger
import json

# Create logger
logger = logging.getLogger('timestamp-test')
logger.setLevel(logging.INFO)

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

# Log a test message
log_data = {
    'event': 'timestamp_test',
    'env': 'development',
    'game_id': 'test123',
    'move_number': 5
}

logger.info("Testing timestamp format", extra=log_data)

# Print the formatted log message
print("\nTimestamp format test complete. Timestamp should be in ISO8601 format (YYYY-MM-DDTHH:MM:SS.sssZ)")