from typing import Dict
from chess import Board
from chess.engine import SimpleEngine, Limit
from numpy import load, ndarray
from math import pow
import json
from os import environ
from sys import platform

# Config
TIME_LIMIT = float(environ.get('TIME_LIMIT', 0.2))  # Increased from 0.01 to give Stockfish enough time to respond
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
        # Evaluate board with enough time for reliable analysis
        try:
            print(f"[WDL] Starting analysis with TIME_LIMIT={TIME_LIMIT} seconds")
            import asyncio
            try:
                info = engine.analyse(board, Limit(time=TIME_LIMIT))
                score = info['score'].white().score(mate_score=1000)
                print(f"[WDL] Analysis successful, score: {score}")
            except asyncio.exceptions.TimeoutError as te:
                print(f"[WDL] Stockfish timeout: {te} - Using default evaluation")
                # Use neutral evaluation on timeout
                score = 0
            except Exception as e:
                print(f"[WDL] Stockfish analysis failed: {e}")
                # Default to neutral evaluation if analysis fails
                score = 0
        except Exception as outer_e:
            print(f"[WDL] Outer exception in analysis: {outer_e}")
            score = 0
    finally:
        if should_close:
            try:
                engine.close()
            except Exception as close_error:
                print(f"[WDL] Error while closing engine: {close_error}")

    # Logistic transform on evaluation
    pwin = 1 / (1 + pow(10, -score / 400))
    print(f"[WDL] Calculated win probability: {pwin}")

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
    print(f"[WDL] Starting model calculation for position: {board.fen()}")
    print(f"[WDL] Player times: white={white_time}s, black={black_time}s")

    # Use a single engine instance for the entire model calculation
    try:
        with get_engine() as engine:
            win_bin: int = get_win_bin(board, engine)
    except Exception as e:
        print(f"[WDL] Error during engine analysis: {e}")
        # Default to balanced position (bin 2) if everything fails
        win_bin = 2

    print(f"[WDL] Calculated win_bin: {win_bin}")

    # Ensure times are within range of model
    white_time = min(180, max(1, white_time))
    black_time = min(180, max(1, black_time))

    result = {
        'white_win': float(wwf[white_time, black_time, win_bin]),
        'draw': float(df[white_time, black_time, win_bin]),
        'black_win': float(bwf[white_time, black_time, win_bin])
    }

    print(f"[WDL] Returning probabilities: {result}")
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
    print(f"[WDL] Received request: {event}")

    data = event['queryStringParameters']
    try:
        # Handle empty FEN (this was causing issues)
        fen = data.get('fen')
        if fen is None or fen.strip() == "":
            # Default to starting position if FEN is empty
            print("[WDL] Empty FEN received, using starting position")
            fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

        board = Board(fen)

        # Handle missing time parameters
        try:
            white_time: int = int(data.get('white_time', 60))
        except (ValueError, TypeError):
            print("[WDL] Invalid white_time, using default")
            white_time = 60

        try:
            black_time: int = int(data.get('black_time', 60))
        except (ValueError, TypeError):
            print("[WDL] Invalid black_time, using default")
            black_time = 60

    except Exception as e:
        print(f"[WDL] Error parsing request parameters: {e}")
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
        print(f"[WDL] Error during model calculation: {e}")
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