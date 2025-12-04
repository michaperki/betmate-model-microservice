from typing import List, Dict, Optional, Tuple
from chess import Board, Move
from chess.engine import SimpleEngine, Limit
import json
import os
import random
from os import environ
from sys import platform
import atexit
import time
from functools import lru_cache
import logging
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
    level_name = environ.get('LOG_LEVEL', 'WARNING').strip().upper()
    return LEVEL_MAP.get(level_name, logging.WARNING)

# Create a structured logger
logger = logging.getLogger("top_moves")
logger.setLevel(get_configured_level())
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
logger.handlers.clear()
logger.addHandler(handler)
logger.propagate = False

def log_event(level: str, event: str, **kwargs):
    """Log a structured event."""
    log_data = {
        'event': event,
        'env': environ.get('NODE_ENV', 'development')
    }
    log_data.update(kwargs)
    getattr(logger, level.lower())(None, extra=log_data)

# Config
DEPTH = int(environ.get('DEPTH', 6))  # Reduced from 10 to lower memory usage
HASH_SIZE = int(environ.get('HASH_SIZE', 128))  # Reduced from 256 to lower memory usage
CACHE_EXPIRY_TIME = int(environ.get('CACHE_EXPIRY_TIME', 300))  # Cache expiry in seconds (5 min default)

# Global engine instance (Singleton pattern)
_ENGINE: Optional[SimpleEngine] = None

# Cache for top moves by position
_TOP_MOVES_CACHE = {}

def get_engine():
    """Return or create a Stockfish engine instance (singleton pattern)."""
    global _ENGINE

    if _ENGINE is None:
        log_event('debug', 'stockfish_init_start')
        STOCKFISH_PATH = environ.get('STOCKFISH_PATH', None)

        if STOCKFISH_PATH and os.path.exists(STOCKFISH_PATH):
            log_event('debug', 'stockfish_init_configured', path=STOCKFISH_PATH)
            _ENGINE = SimpleEngine.popen_uci(STOCKFISH_PATH)
        else:
            try:
                executable = f'stockfish_{"mac" if platform == "darwin" else "linux"}'
                bundled_path = f'./assets/{executable}'
                log_event('debug', 'stockfish_init_bundled', path=bundled_path)
                _ENGINE = SimpleEngine.popen_uci(bundled_path)
            except Exception as e:
                fallback_path = os.path.join(os.getcwd(), "assets", executable)
                log_event('warning', 'stockfish_init_fallback', path=fallback_path, error=str(e))
                _ENGINE = SimpleEngine.popen_uci(fallback_path)

        _ENGINE.configure({"Hash": HASH_SIZE})
        log_event('info', 'service_ready', component='stockfish_engine', hash_size=HASH_SIZE)

        # Register cleanup handler
        atexit.register(cleanup_engine)

    return _ENGINE


def cleanup_engine():
    """Clean up the engine when the application exits."""
    global _ENGINE
    if _ENGINE:
        log_event('info', 'stockfish_shutdown')
        _ENGINE.quit()
        _ENGINE = None


def clean_cache():
    """Remove expired items from the cache."""
    global _TOP_MOVES_CACHE
    current_time = time.time()

    # Create a list of keys to remove to avoid modifying dict during iteration
    keys_to_remove = []
    for key, (timestamp, _) in _TOP_MOVES_CACHE.items():
        if current_time - timestamp > CACHE_EXPIRY_TIME:
            keys_to_remove.append(key)

    # Remove expired items
    for key in keys_to_remove:
        del _TOP_MOVES_CACHE[key]

    if keys_to_remove:
        log_event('debug', 'cache_cleaned', removed_items=len(keys_to_remove), cache_size=len(_TOP_MOVES_CACHE))


def get_move_rating(board: Board, move: Move, engine=None, log_context=None) -> int:
    """
    Get integer rating of `move` on given `board`.
    Rating is approximate and changes on each call.
    Uses the provided engine or creates a new one if not provided.

    Args:
        board: Chess board position
        move: Move to analyze
        engine: Optional pre-initialized Stockfish engine
        log_context: Optional logging context dictionary
    """
    if engine is None:
        engine = get_engine()

    log_ctx = log_context or {}

    try:
        analysis = engine.analyse(board, Limit(depth=DEPTH), root_moves=[move])
        score = analysis.get('score').pov(board.turn).score(mate_score=1000)

        if log_context and random.random() < 0.01:  # Only log occasionally to reduce noise
            log_event('debug', 'move_analysis',
                     move=board.san(move),
                     score=score,
                     **log_ctx)

        return score
    except Exception as e:
        log_event('warning', 'move_analysis_failed',
                 move=str(move),
                 error=str(e),
                 **log_ctx)
        return float('-inf')  # Worst score fallback


def get_cache_key(fen: str, n: int) -> str:
    """Create a unique key for the top moves cache."""
    return f"{fen}|{n}"


def model(board: Board, n: int, game_id: str = None, move_number: int = None) -> List[Dict]:
    """
    Return top `n` moves on `board` with analysis data.
    Uses a single engine instance for all move analysis to prevent memory issues.
    Returns list of dictionaries with move, score, percentile, and is_best_move.

    Args:
        board: Chess board position
        n: Number of top moves to return
        game_id: Optional game ID for correlation in logs
        move_number: Optional move number for correlation in logs
    """
    # Clean expired cache entries occasionally (1% chance)
    if random.random() < 0.01:
        clean_cache()

    # Create context for logging
    fen = board.fen()
    is_whites_turn = " w " in fen
    player_color = "white" if is_whites_turn else "black"

    log_context = {
        'fen': fen,
        'num_moves_requested': n,
        'player_to_move': player_color
    }

    # Add optional game tracking info if provided
    if game_id:
        log_context['game_id'] = game_id
    if move_number is not None:
        log_context['move_number'] = move_number

    # Check cache first
    cache_key = get_cache_key(fen, n)
    current_time = time.time()

    if cache_key in _TOP_MOVES_CACHE:
        timestamp, cached_result = _TOP_MOVES_CACHE[cache_key]
        if current_time - timestamp <= CACHE_EXPIRY_TIME:
            # Sample cache hit logs to reduce noise
            if random.random() < 0.05:  # Only log 5% of cache hits
                log_event('debug', 'top_moves_cache_hit', **log_context)
            return cached_result

    # Not in cache, calculate top moves
    if random.random() < 0.2:  # Log 20% of analysis starts
        log_event('debug', 'top_moves_analysis_start', **log_context)

    move_scores = []
    # Use a single engine instance for all moves to reduce memory usage
    engine = get_engine()

    # Get all legal moves
    legal_moves = list(board.legal_moves)
    log_event('debug', 'legal_moves_count', count=len(legal_moves), **log_context)

    # Analyze each move
    for move in legal_moves:
        try:
            score = get_move_rating(board, move, engine, log_context)
            move_scores.append((board.san(move), score))
        except Exception as e:
            log_event('error', 'move_analysis_error', move=str(move), error=str(e), **log_context)
            move_scores.append((board.san(move), float('-inf')))  # Worst score fallback

    # Sort moves by score (best first)
    sorted_moves = sorted(move_scores, key=lambda x: -x[1])[:n]

    if not sorted_moves:
        log_event('warning', 'no_valid_moves_found', **log_context)
        return []

    # Calculate percentiles relative to the returned moves
    best_score = sorted_moves[0][1]
    worst_score = sorted_moves[-1][1] if len(sorted_moves) > 1 else best_score
    score_range = max(1, best_score - worst_score)  # Avoid division by zero

    result = []
    for i, (move, score) in enumerate(sorted_moves):
        # Calculate percentile (100 for best move, scaled down for others)
        if score_range == 1:  # All moves have same score
            percentile = 100
        else:
            percentile = max(0, min(100, int(((score - worst_score) / score_range) * 100)))

        result.append({
            "move": move,
            "score": score,
            "percentile": percentile,
            "is_best_move": (i == 0)
        })

    # Store in cache
    _TOP_MOVES_CACHE[cache_key] = (current_time, result)

    # Create single comprehensive log event with all the key information
    moves_summary = ", ".join([f"{m['move']}:{m['percentile']}%" for m in result[:3]])
    log_event('info', 'top_moves_analysis_complete',
             top_moves_count=len(result),
             best_move=result[0]['move'] if result else None,
             top_moves=moves_summary,
             **log_context)

    return result


def top_moves_route(event, context=None):
    """
    Handler of AWS Lambda call.
    Parses input and passes it to `model()`.

    Will return 400 if:
    - `fen` is not provided or not in proper notation
    - `n` is not provided, can't be cast to int, or is <=0

    Optional parameters:
    - `enhanced`: if 'true', returns detailed analysis data; otherwise returns just move strings
    - `game_id`: ID of the game for correlation in logs
    - `move_number`: Current move number for correlation in logs

    Otherwise, will return result from `model()` with 200 status.
    """
    # Get trace ID from request if available
    trace_id = None
    if event.get('headers'):
        trace_id = event['headers'].get('x-trace-id')

    # Log with trace ID if available
    log_context = {}
    if trace_id:
        log_context['trace_id'] = trace_id

    log_event('debug', 'top_moves_request_received', **log_context)

    data = event['queryStringParameters']

    try:
        # Extract game_id and move_number if provided
        game_id = data.get('game_id')
        move_number = None
        if 'move_number' in data:
            try:
                move_number = int(data.get('move_number'))
            except (ValueError, TypeError):
                log_event('warning', 'invalid_move_number_ignored', **log_context)

        if game_id:
            log_context['game_id'] = game_id
        if move_number is not None:
            log_context['move_number'] = move_number

        # Extract required parameters
        fen = data.get('fen')
        if not fen or fen.strip() == "":
            log_event('warning', 'empty_fen', **log_context)
            return {
                'statusCode': 400,
                'body': json.dumps({
                    "error": "Argument error",
                    "message": "FEN position is required"
                })
            }

        log_context['fen'] = fen
        board = Board(fen)

        # Record current player from FEN
        player_color = "white" if " w " in fen else "black"
        log_context['player_to_move'] = player_color

        # Get number of moves to return
        n: int = int(data.get('n', 3))  # Default to 3 moves if not specified
        if n <= 0:
            log_event('warning', 'invalid_n_value', n=n, **log_context)
            return {
                'statusCode': 400,
                'body': json.dumps({
                    "error": "Argument error",
                    "message": "'n' must be a positive integer"
                })
            }

        # Check if enhanced format is requested (default to false for backward compatibility)
        enhanced = data.get('enhanced', 'false').lower() == 'true'

    except Exception as e:
        log_event('error', 'request_parsing_error', error=str(e), **log_context)
        return {
            'statusCode': 400,
            'body': json.dumps({
                "error": "Argument error",
                "message": str(e)
            })
        }

    # Pass game_id and move_number to model for correlation
    top_moves_data = model(board, n, game_id, move_number)

    # Return format based on enhanced parameter
    if enhanced:
        # Return enhanced format with analysis data
        response_data = top_moves_data
        log_event('debug', 'enhanced_response_format', move_count=len(top_moves_data), **log_context)
    else:
        # Return legacy format (just move strings) for backward compatibility
        response_data = [move_data['move'] for move_data in top_moves_data]
        log_event('debug', 'legacy_response_format', move_count=len(response_data), **log_context)

    return {
        'statusCode': 200,
        'body': json.dumps({
            "message": "SUCCESS",
            "data": response_data,
            "meta": {
                "game_id": game_id,
                "move_number": move_number,
                "player_to_move": player_color
            } if game_id or move_number else None
        })
    }


def handler(event, context):
    """AWS Lambda handler function"""
    return top_moves_route(event, context)


# --- Local‑dev server (optional) ---------------------------
if __name__ == "__main__" and environ.get("LOCAL_DEV") == "true":
    from flask import Flask, request
    import threading

    lock = threading.Lock()
    app = Flask(__name__)

    @app.route("/predict", methods=["POST"])
    def predict_route():
        data = request.get_json(force=True).get("queryStringParameters", {})
        log_event('debug', 'local_dev_request', data=data)
        with lock:
            return top_moves_route({"queryStringParameters": data})

    # Suppress Flask's built-in logging to avoid duplication
    import logging
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.ERROR)

    # Warm the engine for faster local calls
    get_engine()

    # Log a clear service_ready event
    port = 8080
    log_event('info', 'service_ready',
              component='top_moves_service',
              endpoint=f"http://localhost:{port}/predict",
              depth=DEPTH,
              environment=environ.get('NODE_ENV', 'development'),
              cache_expiry_seconds=CACHE_EXPIRY_TIME)

    app.run(host="0.0.0.0", port=port, threaded=False)
