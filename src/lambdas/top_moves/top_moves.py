from typing import List
from chess import Board, Move
from chess.engine import SimpleEngine, Limit
import json
from os import environ
from sys import platform

# Config
DEPTH = int(environ.get('DEPTH', 10))
HASH_SIZE = int(environ.get('HASH_SIZE', 256))

def get_engine():
    """
    Create and return a new Stockfish engine instance.
    This function will use the system-installed Stockfish if STOCKFISH_PATH is set,
    otherwise it falls back to the bundled binary.
    The returned engine supports context manager protocol for automatic cleanup.
    """
    STOCKFISH_PATH = environ.get('STOCKFISH_PATH', None)
    if STOCKFISH_PATH:
        # Use system-installed Stockfish if environment variable is set
        engine = SimpleEngine.popen_uci(STOCKFISH_PATH)
    else:
        # Fall back to bundled binary if no environment variable
        executable = f'stockfish_{"mac" if platform == "darwin" else "linux"}'
        engine = SimpleEngine.popen_uci(f'./assets/{executable}')
    engine.configure({"Hash": HASH_SIZE})
    return engine


def get_move_rating(board: Board, move: Move) -> int:
    """
    Get integer rating of `move` on given `board`.
    Rating is approximate and changes on each call.
    Creates a new engine instance per call for better stability.
    """
    with get_engine() as engine:
        analysis = engine.analyse(board, Limit(depth=DEPTH), root_moves=[move])
        return analysis.get('score').pov(board.turn).score(mate_score=1000)


def model(board: Board, n: int) -> List[str]:
    """
    Return top `n` moves on `board` in SAN notation.
    Move ratings are approximate and will change on each call.
    """
    # Create a single engine instance for all move ratings in this request
    engine = get_engine()
    try:
        # Modified function to use the shared engine
        def get_move_rating_with_engine(move):
            analysis = engine.analyse(board, Limit(depth=DEPTH), root_moves=[move])
            return analysis.get('score').pov(board.turn).score(mate_score=1000)

        move_scores = [(board.san(move), get_move_rating_with_engine(move))
                       for move in board.legal_moves]

        return [move for move, _ in sorted(move_scores, key=lambda x: -x[1])[:n]]
    finally:
        # Ensure engine is always closed properly
        engine.quit()


def top_moves_route(event, context=None):
    """
    Handler of AWS Lambda call.
    Parses input and passes it to `model()`.

    Will return 400 if:
    - `fen` is not provided or not in proper notation
    - `n` is not provided, can't be cast to int, or is <=0

    Otherwise, will return result from `model()` with 200 status.
    """
    data = event['queryStringParameters']
    print("Received request:", data)
    try:
        board = Board(data['fen'])
        n: int = int(data['n'])
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

    top_moves = model(board, n)

    return {
        'statusCode': 200,
        'body': json.dumps({
            "message": "SUCCESS",
            "data": top_moves
        })
    }

if __name__ == "__main__":
    from flask import Flask, request

    app = Flask(__name__)

    @app.route("/predict", methods=["POST"])
    def route():
        data = request.get_json(force=True).get("queryStringParameters", {})
        # print("[top-moves] Received request with FEN:", data.get("fen"), "n =", data.get("n"))
        return top_moves_route({"queryStringParameters": data})

    app.run(host="0.0.0.0", port=8080)
