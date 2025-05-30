#!/usr/bin/env python3
"""
Test script for normalized timestamp formatting in loggers
"""
import sys
import os
import time
from src.lambdas.wdl.logger import log_event as wdl_log_event
from src.shared_logger import setup_logger, log_event as shared_log_event

# Test WDL logger
print("Testing WDL Logger:")
wdl_log_event('info', 'test_normalized_timestamp', trace_id='test123', game_id='game456', move_number=5)

# Test shared logger
print("\nTesting Shared Logger:")
logger = setup_logger('test-service')
shared_log_event(logger, 'info', 'test_normalized_timestamp', trace_id='test123', game_id='game456', move_number=5)

# Test axiom logger if available
try:
    print("\nTesting Axiom Logger:")
    from src.axiom_logger import log_event as axiom_log_event
    axiom_log_event('info', 'test_normalized_timestamp', trace_id='test123', game_id='game456', move_number=5)
except ImportError:
    print("Axiom logger not available")

print("\nLog testing complete. Check the timestamp format in the logs above.")