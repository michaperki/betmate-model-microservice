from typing import Dict, List, Tuple
from chess import Board, Move
from chess.engine import SimpleEngine, Limit
import json
from os import environ
from sys import platform

# Config
DEPTH = int(environ.get('DEPTH', 10))
HASH_SIZE = int(environ.get('HASH_SIZE', 256))

def get_engine():
    """Create and return a new Stockfish engine instance for each request."""
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
    """
    engine = get_engine()
    try:
        analysis = engine.analyse(board, Limit(depth=DEPTH), root_moves=[move])
        return analysis.get('score').pov(board.turn).score(mate_score=1000)
    finally:
        engine.quit()


def get_all_move_ratings(board: Board) -> Dict[str, Dict]:
    """
    Return ratings for all legal moves on `board`.
    
    Returns a dictionary where:
    - Keys are move strings in SAN notation
    - Values are dictionaries containing:
      - "score": Raw engine score
      - "percentile": Percentile rank compared to best move (0-100)
    """
    if not board.legal_moves:
        return {}
    
    # Get all moves with scores
    move_scores: List[Tuple[str, int]] = []
    for move in board.legal_moves:
        san = board.san(move)
        score = get_move_rating(board, move)
        move_scores.append((san, score))
    
    # Sort moves by score (highest to lowest)
    sorted_moves = sorted(move_scores, key=lambda x: -x[1])
    
    # Get best and worst scores
    best_score = sorted_moves[0][1]
    worst_score = sorted_moves[-1][1]
    score_range = max(1, best_score - worst_score)  # Avoid division by zero
    
    # Calculate percentiles
    result = {}
    for san, score in sorted_moves:
        # If score matches the best score, it's 100%
        if score == best_score:
            percentile = 100
        else:
            # Normalize to 0-100 scale
            percentile = int(((score - worst_score) / score_range) * 100)
        
        result[san] = {
            "score": score,
            "percentile": percentile
        }
    
    return result


def analyze_move(board: Board, move_san: str) -> Dict:
    """
    Analyze a specific move on the given board.
    
    Returns a dictionary with:
    - "score": Raw engine score
    - "percentile": Percentile rank compared to best move (0-100)
    - "is_best_move": Boolean, true if move is the engine's top choice
    """
    # Get ratings for all moves
    all_ratings = get_all_move_ratings(board)
    
    # Check if the requested move is legal
    if move_san not in all_ratings:
        return {
            "error": "Invalid move",
            "valid_moves": list(all_ratings.keys())
        }
    
    # Get the move's data
    move_data = all_ratings[move_san]
    
    # Find best move score
    best_move = max(all_ratings.items(), key=lambda x: x[1]["score"])
    
    # Add additional info
    move_data["is_best_move"] = (move_san == best_move[0])
    
    return move_data


def move_analysis_route(event, context=None):
    """
    Handler of AWS Lambda call for analyzing a specific move.
    
    Required parameters:
    - fen: Board position in FEN notation
    - move: Move to analyze in SAN notation
    
    Returns:
    - Analysis result with score and percentile
    - 400 if parameters are invalid
    """
    data = event['queryStringParameters']
    print("Received request:", data)
    
    try:
        board = Board(data['fen'])
        move_san = data['move']
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps({
                "error": "Argument error",
                "message": str(e)
            })
        }
    
    analysis = analyze_move(board, move_san)
    
    # If there was an error, return it with 400 status
    if "error" in analysis:
        return {
            'statusCode': 400,
            'body': json.dumps(analysis)
        }
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            "message": "SUCCESS",
            "data": analysis
        })
    }


def all_moves_analysis_route(event, context=None):
    """
    Handler of AWS Lambda call for analyzing all legal moves.
    
    Required parameters:
    - fen: Board position in FEN notation
    
    Returns:
    - Analysis result for all legal moves
    - 400 if parameters are invalid
    """
    data = event['queryStringParameters']
    print("Received request:", data)
    
    try:
        board = Board(data['fen'])
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps({
                "error": "Argument error",
                "message": str(e)
            })
        }
    
    all_ratings = get_all_move_ratings(board)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            "message": "SUCCESS",
            "data": all_ratings
        })
    }


if __name__ == "__main__":
    from flask import Flask, request

    app = Flask(__name__)

    # Add the main predict route that the router expects
    @app.route("/predict", methods=["POST"])
    def predict_route():
        data = request.get_json(force=True).get("queryStringParameters", {})
        return move_analysis_route({"queryStringParameters": data})

    # Keep the original routes for direct access
    @app.route("/analyze-move", methods=["POST"])
    def analyze_move_route():
        data = request.get_json(force=True).get("queryStringParameters", {})
        return move_analysis_route({"queryStringParameters": data})

    @app.route("/analyze-all-moves", methods=["POST"])
    def analyze_all_moves_route():
        data = request.get_json(force=True).get("queryStringParameters", {})
        return all_moves_analysis_route({"queryStringParameters": data})

    print("Move analysis service starting on port 8080...")
    app.run(host="0.0.0.0", port=8080)