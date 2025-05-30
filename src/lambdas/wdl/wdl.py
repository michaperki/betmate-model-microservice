from typing import Dict, Optional, Tuple
from chess import Board
from chess.engine import SimpleEngine, Limit
from numpy import load, ndarray
from math import pow
import json
from os import environ
from sys import platform
import atexit
import os
import time
import random
from functools import lru_cache
from logger import log_event

# Config
TIME_LIMIT = float(environ.get('TIME_LIMIT', 0.2))  # Increased from 0.01 to give Stockfish enough time to respond
HASH_SIZE = int(environ.get('HASH_SIZE', 128))  # Reduced from 256 to lower memory usage
CACHE_EXPIRY_TIME = int(environ.get('CACHE_EXPIRY_TIME', 300))  # Cache expiry in seconds (5 min default)

# Global engine instance (Singleton pattern)
_ENGINE: Optional[SimpleEngine] = None

# Result cache to avoid redundant WDL computations
_CACHE = {}

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
                log_event('debug', 'stockfish_init_fallback', path=fallback_path)
                _ENGINE = SimpleEngine.popen_uci(fallback_path)

        _ENGINE.configure({"Hash": HASH_SIZE})
        log_event('info', 'stockfish_init_success', hash_size=HASH_SIZE)
        print(f"Successfully initialized Stockfish from {STOCKFISH_PATH or bundled_path}")

        # Register cleanup handler
        atexit.register(cleanup_engine)

    # Engine is already cached, no need to log anything
    return _ENGINE


def cleanup_engine():
    """Clean up the engine when the application exits."""
    global _ENGINE
    if _ENGINE:
        print("Shutting down Stockfish engine...")
        _ENGINE.quit()
        _ENGINE = None


# Load model data at module level for Lambda cold start
try:
    with open('./assets/black_win_fraction.npy', 'rb') as f:
        bwf: ndarray = load(f)
    with open('./assets/white_win_fraction.npy', 'rb') as f:
        wwf: ndarray = load(f)
    with open('./assets/draw_fraction.npy', 'rb') as f:
        df: ndarray = load(f)
    log_event('info', 'model_data_loaded')
except Exception as e:
    log_event('error', 'model_data_load_failed', error=str(e))
    # Create dummy model data for fallback
    import numpy as np
    log_event('warning', 'using_fallback_model_data')
    shape = (181, 181, 5)  # Max time 180 seconds + 1 for indexing, 5 bins
    bwf = np.full(shape, 0.33)
    wwf = np.full(shape, 0.33)
    df = np.full(shape, 0.34)


def clean_cache():
    """Remove expired items from the cache."""
    global _CACHE
    current_time = time.time()

    # Create a list of keys to remove to avoid modifying dict during iteration
    keys_to_remove = []
    for key, (timestamp, _) in _CACHE.items():
        if current_time - timestamp > CACHE_EXPIRY_TIME:
            keys_to_remove.append(key)

    # Remove expired items
    for key in keys_to_remove:
        del _CACHE[key]

    if keys_to_remove:
        log_event('debug', 'cache_cleaned', removed_items=len(keys_to_remove), cache_size=len(_CACHE))


# Using functools.lru_cache for the CPU-intensive part of the computation
@lru_cache(maxsize=128)
def _compute_win_bin_cached(fen: str) -> int:
    """
    Core computation logic for win_bin, cached by FEN string.
    This function is separated to enable effective caching.
    """
    board = Board(fen)
    engine = get_engine()

    try:
        # Evaluate board with enough time for reliable analysis
        try:
            import asyncio
            try:
                info = engine.analyse(board, Limit(time=TIME_LIMIT))
                score = info['score'].white().score(mate_score=1000)
                # No debug log here to reduce noise - will log in the wrapper function
            except asyncio.exceptions.TimeoutError as te:
                log_event('warning', 'stockfish_timeout', error=str(te), fen=fen)
                # Use neutral evaluation on timeout
                score = 0
            except Exception as e:
                log_event('warning', 'stockfish_analysis_failed', error=str(e), fen=fen)
                # Default to neutral evaluation if analysis fails
                score = 0
        except Exception as outer_e:
            log_event('error', 'stockfish_outer_exception', error=str(outer_e), fen=fen)
            score = 0
    except Exception as e:
        log_event('error', 'engine_handling_error', error=str(e), fen=fen)
        score = 0

    # Logistic transform on evaluation
    pwin = 1 / (1 + pow(10, -score / 400))

    if pwin < 0.10:
        return 0
    elif pwin >= 0.10 and pwin < 0.40:
        return 1
    elif pwin >= 0.40 and pwin < 0.60:
        return 2
    elif pwin >= 0.60 and pwin < 0.90:
        return 3
    else:  # pwin >= 0.90
        return 4


def get_win_bin(board: Board, engine=None) -> int:
    """
    Convert `board` state to 'bin' corresponding to 'white vs. black' favorability.
    Uses the provided engine instance or creates a temporary one if None.

    This function implements a two-level caching strategy:
    1. First checks the in-memory dict cache with timestamps for recently computed positions
    2. Then uses the LRU cache for frequently computed positions (even if not recent)
    """
    # Clean expired entries occasionally (1% chance each call, to avoid overhead)
    if random.random() < 0.01:
        clean_cache()

    # Convert board to FEN for cache key
    fen = board.fen()
    current_time = time.time()

    # Check if we have a cached result
    if fen in _CACHE:
        timestamp, win_bin = _CACHE[fen]
        # Only use cache if not expired
        if current_time - timestamp <= CACHE_EXPIRY_TIME:
            log_event('debug', 'win_bin_cache_hit', fen=fen)
            return win_bin

    # Not in recent cache, try LRU cache or compute new value
    win_bin = _compute_win_bin_cached(fen)

    # Store in timestamp cache
    _CACHE[fen] = (current_time, win_bin)

    # Only log for new computations, but sample to reduce noise
    if random.random() < 0.1:  # Only log 10% of calculations to reduce volume
        log_event('debug', 'win_probability_calculated', pwin_bin=win_bin, fen=fen)

    return win_bin


def get_result_key(fen: str, white_time: int, black_time: int) -> str:
    """Create a cache key for the results cache."""
    return f"{fen}|{white_time}|{black_time}"


# Cache for the final WDL results
_RESULT_CACHE = {}


def model(board: Board, white_time: int, black_time: int, game_id: str = None, move_number: int = None) -> Dict[str, float]:
    """
    Get win/draw/loss probabilities based on `board` state and player times.

    Args:
        board: Chess board position
        white_time: White player's remaining time in seconds
        black_time: Black player's remaining time in seconds
        game_id: Optional game ID for logging correlation
        move_number: Optional move number for logging correlation

    Returns:
        Dictionary with white_win, draw, and black_win probabilities
    """
    fen = board.fen()
    is_whites_turn = " w " in fen
    player_color = "white" if is_whites_turn else "black"

    # Create and log correlation ID for this calculation
    log_context = {
        'fen': fen,
        'white_time': white_time,
        'black_time': black_time,
        'player_to_move': player_color
    }

    # Add optional game tracking info if provided
    if game_id:
        log_context['game_id'] = game_id
    if move_number is not None:
        log_context['move_number'] = move_number

    # Check results cache first
    cache_key = get_result_key(fen, white_time, black_time)
    current_time = time.time()

    if cache_key in _RESULT_CACHE:
        timestamp, result = _RESULT_CACHE[cache_key]
        if current_time - timestamp <= CACHE_EXPIRY_TIME:
            # Sample cache hit logs to reduce noise
            if random.random() < 0.05:  # Only log 5% of cache hits
                log_event('debug', 'model_calculation_cache_hit', **log_context)
            return result

    # Use 'debug' for start but sample to reduce log volume
    if random.random() < 0.2:  # Log 20% of calculation starts
        log_event('debug', 'model_calculation_start', **log_context)

    # Ensure times are within range of model
    white_time_adjusted = min(180, max(1, white_time))
    black_time_adjusted = min(180, max(1, black_time))

    if white_time_adjusted != white_time or black_time_adjusted != black_time:
        log_event('debug', 'time_adjusted',
                 original_white=white_time,
                 adjusted_white=white_time_adjusted,
                 original_black=black_time,
                 adjusted_black=black_time_adjusted)

    # Use a single engine instance for the entire model calculation
    try:
        win_bin: int = get_win_bin(board, get_engine())
    except Exception as e:
        log_event('error', 'engine_analysis_error', error=str(e), **log_context)
        # Default to balanced position (bin 2) if everything fails
        win_bin = 2

    # Calculate result from lookup table using adjusted times
    result = {
        'white_win': float(wwf[white_time_adjusted, black_time_adjusted, win_bin]),
        'draw': float(df[white_time_adjusted, black_time_adjusted, win_bin]),
        'black_win': float(bwf[white_time_adjusted, black_time_adjusted, win_bin])
    }

    # Store in cache
    _RESULT_CACHE[cache_key] = (current_time, result)

    # Create a summary log with all relevant information in one place
    log_event('info', 'move_analysis_complete',
             win_bin=win_bin,
             probabilities=result,
             **log_context)

    return result


def wdl_route(event, context=None):
    """
    Handler of AWS Lambda call.
    Parses input and passes it to `model()`.

    Will return 400 if:
    - `fen` is not provided or not in proper notation
    - `white_time` is not provided or can't be cast to int
    - `black_time` is not provided or can't be cast to int

    Optional parameters:
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

    log_event('debug', 'wdl_request_received', **log_context)

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

        # Handle empty FEN (this was causing issues)
        fen = data.get('fen')
        if fen is None or fen.strip() == "":
            # Default to starting position if FEN is empty
            log_event('warning', 'empty_fen_using_default', **log_context)
            fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

        board = Board(fen)
        log_context['fen'] = fen

        # Record current player from FEN
        player_color = "white" if " w " in fen else "black"
        log_context['player_to_move'] = player_color

        # Handle missing time parameters
        try:
            white_time: int = int(data.get('white_time', 60))
            log_context['white_time'] = white_time
        except (ValueError, TypeError):
            log_event('warning', 'invalid_white_time_using_default', **log_context)
            white_time = 60
            log_context['white_time'] = white_time

        try:
            black_time: int = int(data.get('black_time', 60))
            log_context['black_time'] = black_time
        except (ValueError, TypeError):
            log_event('warning', 'invalid_black_time_using_default', **log_context)
            black_time = 60
            log_context['black_time'] = black_time

    except Exception as e:
        log_event('error', 'request_parsing_error', error=str(e), **log_context)
        return {
            'statusCode': 400,
            'body': json.dumps({
                "error": "Argument error",
                "message": str(e)
            })
        }

    try:
        # Pass game_id and move_number to model for correlation
        probabilities = model(board, white_time, black_time, game_id, move_number)

        return {
            'statusCode': 200,
            'body': json.dumps({
                "message": "SUCCESS",
                "data": probabilities,
                "meta": {
                    "game_id": game_id,
                    "move_number": move_number,
                    "player_to_move": player_color
                } if game_id or move_number else None
            })
        }
    except Exception as e:
        log_event('error', 'model_calculation_failed', error=str(e), **log_context)
        # Return default probabilities if model fails
        return {
            'statusCode': 200,  # Return 200 to avoid client errors
            'body': json.dumps({
                "message": "WARNING: Used fallback values due to analysis error",
                "data": {
                    "white_win": 0.33,
                    "draw": 0.34,
                    "black_win": 0.33
                },
                "meta": {
                    "game_id": game_id,
                    "move_number": move_number,
                    "player_to_move": player_color,
                    "error": str(e)
                } if game_id or move_number else {"error": str(e)}
            })
        }


def handler(event, context):
    """AWS Lambda handler function"""
    return wdl_route(event, context)


# --- Local‑dev server (optional) ---------------------------
if __name__ == "__main__" and environ.get("LOCAL_DEV") == "true":
    from flask import Flask, request
    import threading

    lock = threading.Lock()
    app = Flask(__name__)

    @app.route("/predict", methods=["POST"])
    def predict_route():
        data = request.get_json(force=True).get("queryStringParameters", {})
        with lock:
            return wdl_route({"queryStringParameters": data})

    # Warm the engine for faster local calls
    get_engine()
    log_event('info', 'local_dev_server_starting', port=8080)
    app.run(host="0.0.0.0", port=8080, threaded=False)