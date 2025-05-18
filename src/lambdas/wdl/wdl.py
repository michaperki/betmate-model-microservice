from typing import Dict
from chess import Board
from chess.engine import SimpleEngine, Limit
from numpy import load, ndarray
from math import pow
import json
from os import environ
from sys import platform

# Config
TIME_LIMIT = float(environ.get('TIME_LIMIT', 0.01))  # Reduced from 0.1 to lower memory usage
HASH_SIZE = int(environ.get('HASH_SIZE', 128))  # Reduced from 256 to lower memory usage

def get_engine():
    """Create and return a new Stockfish engine instance for each request."""
    # Try primary path (system-installed Stockfish)
    STOCKFISH_PATH = environ.get('STOCKFISH_PATH', '/usr/games/stockfish')

    try:
        engine = SimpleEngine.popen_uci(STOCKFISH_PATH)
        print(f"Successfully initialized Stockfish from {STOCKFISH_PATH}")
    except Exception as e:
        # Fallback to bundled binary if system path fails
        print(f"Failed to load Stockfish from {STOCKFISH_PATH}: {e}")
        print("Trying bundled binary as fallback...")
        try:
            engine = SimpleEngine.popen_uci("./assets/stockfish_linux")
            print("Successfully initialized Stockfish from bundled binary")
        except Exception as e2:
            # One final attempt with absolute path
            import os
            fallback_path = os.path.join(os.getcwd(), "assets", "stockfish_linux")
            print(f"Trying absolute path: {fallback_path}")
            engine = SimpleEngine.popen_uci(fallback_path)
            print(f"Successfully initialized Stockfish from {fallback_path}")

    engine.configure({"Hash": HASH_SIZE})
    return engine

# Load model
with open('./assets/black_win_fraction.npy', 'rb') as f:
    bwf: ndarray = load(f)
with open('./assets/white_win_fraction.npy', 'rb') as f:
    wwf: ndarray = load(f)
with open('./assets/draw_fraction.npy', 'rb') as f:
    df: ndarray = load(f)


def get_win_bin(board: Board, engine=None) -> int:
    """
    Convert `board` state to 'bin' corresponding to 'white vs. black' favorability.
    Uses the provided engine instance or creates a temporary one if None.
    """
    should_close = False
    if engine is None:
        engine = get_engine()
        should_close = True
    
    try:
        # Evaluate board with a very short time limit to reduce memory usage
        info = engine.analyse(board, Limit(time=TIME_LIMIT))
        score = info['score'].white().score(mate_score=1000)
    finally:
        if should_close:
            engine.close()

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
    elif pwin >= 0.00:
        return 4


def model(board: Board, white_time: int, black_time: int) -> Dict[str, float]:
    """Get win/draw/loss probabilities based on `board` state and player times."""
    # Use a single engine instance for the entire model calculation
    with get_engine() as engine:
        win_bin: int = get_win_bin(board, engine)

    # Ensure times are within range of model
    white_time = min(180, max(1, white_time))
    black_time = min(180, max(1, black_time))

    return {
        'white_win': wwf[white_time, black_time, win_bin],
        'draw': df[white_time, black_time, win_bin],
        'black_win': bwf[white_time, black_time, win_bin]
    }


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
    data = event['queryStringParameters']
    try:
        board = Board(data['fen'])
        white_time: int = int(data['white_time'])
        black_time: int = int(data['black_time'])
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps({
                "error": "Argument error",
                "message": str(e)
            })
        }

    probabilities = model(board, white_time, black_time)

    return {
        'statusCode': 200,
        'body': json.dumps({
            "message": "SUCCESS",
            "data": probabilities
        })
    }

if __name__ == "__main__":
    from flask import Flask, request
    import threading

    app = Flask(__name__)
    
    # Add a lock to prevent multiple concurrent analyses
    # This helps avoid resource contention and engine crashes
    stockfish_lock = threading.Lock()

    @app.route("/predict", methods=["POST"])
    def route():
        data = request.get_json(force=True).get("queryStringParameters", {})
        print("[wdl] Received request - acquiring lock")
        
        # Use lock to ensure only one Stockfish instance runs at a time
        with stockfish_lock:
            print("[wdl] Lock acquired, processing request")
            result = wdl_route({"queryStringParameters": data})
            print("[wdl] Request processed, releasing lock")
            return result

    # Limit to only 1 worker thread to prevent concurrent Stockfish instances
    app.run(host="0.0.0.0", port=8080, threaded=False)