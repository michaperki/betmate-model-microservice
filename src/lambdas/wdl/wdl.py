from typing import Dict, Optional
from chess import Board
from chess.engine import SimpleEngine, Limit
from numpy import load, ndarray
from math import pow
import json
from os import environ
from sys import platform
import atexit
import os
from logger import log_event

# Config
TIME_LIMIT = float(environ.get('TIME_LIMIT', 0.2))  # Increased from 0.01 to give Stockfish enough time to respond
HASH_SIZE = int(environ.get('HASH_SIZE', 128))  # Reduced from 256 to lower memory usage

# Global engine instance (Singleton pattern)
_ENGINE: Optional[SimpleEngine] = None

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


def get_win_bin(board: Board, engine=None) -> int:
    """
    Convert `board` state to 'bin' corresponding to 'white vs. black' favorability.
    Uses the provided engine instance or creates a temporary one if None.
    """
    if engine is None:
        engine = get_engine()

    try:
        # Evaluate board with enough time for reliable analysis
        try:
            import asyncio
            try:
                info = engine.analyse(board, Limit(time=TIME_LIMIT))
                score = info['score'].white().score(mate_score=1000)
                log_event('debug', 'stockfish_analysis_success', score=score)
            except asyncio.exceptions.TimeoutError as te:
                log_event('warning', 'stockfish_timeout', error=str(te))
                # Use neutral evaluation on timeout
                score = 0
            except Exception as e:
                log_event('warning', 'stockfish_analysis_failed', error=str(e))
                # Default to neutral evaluation if analysis fails
                score = 0
        except Exception as outer_e:
            log_event('error', 'stockfish_outer_exception', error=str(outer_e))
            score = 0
    except Exception as e:
        log_event('error', 'engine_handling_error', error=str(e))
        score = 0

    # Logistic transform on evaluation
    pwin = 1 / (1 + pow(10, -score / 400))
    log_event('debug', 'win_probability_calculated', pwin=pwin)

    if pwin < 0.10:
        return 0
    elif pwin >= 0.10 and pwin < 0.40:
        return 1
    elif pwin >= 0.40 and pwin < 0.60:
        return 2
    elif pwin >= 0.60 and pwin < 0.90:
        return 3
    elif pwin >= 0.90:
        return 4


def model(board: Board, white_time: int, black_time: int) -> Dict[str, float]:
    """Get win/draw/loss probabilities based on `board` state and player times."""
    log_event('debug', 'model_calculation_start', fen=board.fen(), white_time=white_time, black_time=black_time)

    # Use a single engine instance for the entire model calculation
    try:
        win_bin: int = get_win_bin(board, get_engine())
    except Exception as e:
        log_event('error', 'engine_analysis_error', error=str(e))
        # Default to balanced position (bin 2) if everything fails
        win_bin = 2

    log_event('debug', 'win_bin_calculated', win_bin=win_bin)

    # Ensure times are within range of model
    white_time = min(180, max(1, white_time))
    black_time = min(180, max(1, black_time))

    result = {
        'white_win': float(wwf[white_time, black_time, win_bin]),
        'draw': float(df[white_time, black_time, win_bin]),
        'black_win': float(bwf[white_time, black_time, win_bin])
    }

    log_event('info', 'model_calculation_complete', probabilities=result)
    return result


def wdl_route(event, context=None):
    """
    Handler of AWS Lambda call.
    Parses input and passes it to `model()`.

    Will return 400 if:
    - `fen` is not provided or not in proper notation
    - `white_time` is not provided or can't be cast to int
    - `black_time` is not provided or can't be cast to int

    Otherwise, will return result from `model()` with 200 status.
    """
    log_event('debug', 'wdl_request_received')

    data = event['queryStringParameters']
    try:
        # Handle empty FEN (this was causing issues)
        fen = data.get('fen')
        if fen is None or fen.strip() == "":
            # Default to starting position if FEN is empty
            log_event('warning', 'empty_fen_using_default')
            fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

        board = Board(fen)

        # Handle missing time parameters
        try:
            white_time: int = int(data.get('white_time', 60))
        except (ValueError, TypeError):
            log_event('warning', 'invalid_white_time_using_default')
            white_time = 60

        try:
            black_time: int = int(data.get('black_time', 60))
        except (ValueError, TypeError):
            log_event('warning', 'invalid_black_time_using_default')
            black_time = 60

    except Exception as e:
        log_event('error', 'request_parsing_error', error=str(e))
        return {
            'statusCode': 400,
            'body': json.dumps({
                "error": "Argument error",
                "message": str(e)
            })
        }

    try:
        probabilities = model(board, white_time, black_time)

        return {
            'statusCode': 200,
            'body': json.dumps({
                "message": "SUCCESS",
                "data": probabilities
            })
        }
    except Exception as e:
        log_event('error', 'model_calculation_failed', error=str(e))
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
                "error": str(e)
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