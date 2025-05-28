from typing import List, Dict, Optional
from chess import Board, Move
from chess.engine import SimpleEngine, Limit
import json
from os import environ
from sys import platform
import atexit

# Config
DEPTH = int(environ.get('DEPTH', 6))  # Reduced from 10 to lower memory usage
HASH_SIZE = int(environ.get('HASH_SIZE', 128))  # Reduced from 256 to lower memory usage

# Global engine instance (Singleton pattern)
_ENGINE: Optional[SimpleEngine] = None

def get_engine():
    """Return or create a Stockfish engine instance (singleton pattern)."""
    global _ENGINE

    if _ENGINE is None:
        print("Initializing Stockfish engine...")
        STOCKFISH_PATH = environ.get('STOCKFISH_PATH', None)
        if STOCKFISH_PATH:
            # Use system-installed Stockfish if environment variable is set
            _ENGINE = SimpleEngine.popen_uci(STOCKFISH_PATH)
        else:
            # Fall back to bundled binary if no environment variable
            executable = f'stockfish_{"mac" if platform == "darwin" else "linux"}'
            _ENGINE = SimpleEngine.popen_uci(f'./assets/{executable}')
        _ENGINE.configure({"Hash": HASH_SIZE})

        # Register cleanup handler
        atexit.register(cleanup_engine)

    return _ENGINE


def cleanup_engine():
    """Clean up the engine when the application exits."""
    global _ENGINE
    if _ENGINE:
        print("Shutting down Stockfish engine...")
        _ENGINE.quit()
        _ENGINE = None


def get_move_rating(board: Board, move: Move, engine=None) -> int:
    """
    Get integer rating of `move` on given `board`.
    Rating is approximate and changes on each call.
    Uses the provided engine or creates a new one if not provided.
    """
    if engine is None:
        engine = get_engine()

    analysis = engine.analyse(board, Limit(depth=DEPTH), root_moves=[move])
    return analysis.get('score').pov(board.turn).score(mate_score=1000)


def model(board: Board, n: int) -> List[Dict]:
    """
    Return top `n` moves on `board` with analysis data.
    Uses a single engine instance for all move analysis to prevent memory issues.
    Returns list of dictionaries with move, score, percentile, and is_best_move.
    """
    move_scores = []
    # Use a single engine instance for all moves to reduce memory usage
    engine = get_engine()
    for move in board.legal_moves:
        try:
            analysis = engine.analyse(board, Limit(depth=DEPTH), root_moves=[move])
            score = analysis.get('score').pov(board.turn).score(mate_score=1000)
            move_scores.append((board.san(move), score))
        except Exception as e:
            print(f"Error analyzing move {move}: {e}")
            move_scores.append((board.san(move), float('-inf')))  # Worst score fallback

    # Sort moves by score (best first)
    sorted_moves = sorted(move_scores, key=lambda x: -x[1])[:n]

    if not sorted_moves:
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

    return result


def top_moves_route(event, context=None):
    """
    Handler of AWS Lambda call.
    Parses input and passes it to `model()`.

    Will return 400 if:
    - `fen` is not provided or not in proper notation
    - `n` is not provided, can't be cast to int, or is <=0

    Otherwise, will return result from `model()` with 200 status.

    Parameters:
    - enhanced: if 'true', returns detailed analysis data; otherwise returns just move strings
    """
    data = event['queryStringParameters']
    print("Received request:", data)
    try:
        board = Board(data['fen'])
        n: int = int(data['n'])
        # Check if enhanced format is requested (default to false for backward compatibility)
        enhanced = data.get('enhanced', 'false').lower() == 'true'
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps({
                "error": "Argument error",
                "message": str(e)
            })
        }

    if n <= 0:
        return {
            'statusCode': 400,
            'body': json.dumps({
                "error": "Argument error",
                "message": "'n' must be a positive integer"
            })
        }

    top_moves_data = model(board, n)

    # Return format based on enhanced parameter
    if enhanced:
        # Return enhanced format with analysis data
        response_data = top_moves_data
        print(f"Enhanced response: {len(top_moves_data)} moves with analysis")
    else:
        # Return legacy format (just move strings) for backward compatibility
        response_data = [move_data['move'] for move_data in top_moves_data]
        print(f"Legacy response: {len(response_data)} move strings")

    return {
        'statusCode': 200,
        'body': json.dumps({
            "message": "SUCCESS",
            "data": response_data
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
        with lock:
            return top_moves_route({"queryStringParameters": data})

    # Warm the engine for faster local calls
    get_engine()
    print("[top-moves] Local dev server on :8080 (depth=%d)" % DEPTH)
    app.run(host="0.0.0.0", port=8080, threaded=False)
