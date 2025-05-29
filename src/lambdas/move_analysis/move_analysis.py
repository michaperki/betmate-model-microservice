from typing import Dict, List, Tuple, Optional
from chess import Board, Move
from chess.engine import SimpleEngine, Limit
import json
from os import environ
from sys import platform
import atexit
import os
import sys

# Add the parent directory to sys.path to import the shared axiom_logger
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    from axiom_logger import log_event, generate_trace_id
except ImportError:
    # Fall back to local logger if axiom_logger is not available
    from logger import log_event

    def generate_trace_id():
        """Generate a random trace ID for request correlation."""
        import random
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

# Config
DEPTH = int(environ.get('DEPTH', 6))  # Lower default depth to reduce memory usage
HASH_SIZE = int(environ.get('HASH_SIZE', 128))

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
                log_event('debug', 'stockfish_init_fallback', path=fallback_path, error=str(e))
                _ENGINE = SimpleEngine.popen_uci(fallback_path)

        _ENGINE.configure({"Hash": HASH_SIZE})
        log_event('info', 'stockfish_init_success', hash_size=HASH_SIZE)
        print(f"Successfully initialized Stockfish engine")

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


def get_move_rating(board: Board, move: Move) -> int:
    """
    Get integer rating of `move` on given `board`.
    Rating is approximate and changes on each call.
    """
    engine = get_engine()
    move_san = board.san(move)
    log_event('debug', 'move_analysis_start', move=move_san, depth=DEPTH)

    # Make a copy of the board and apply the move
    try:
        # Create a new board to avoid modifying the original
        analysis_board = board.copy()
        # Apply the move
        analysis_board.push(move)

        # Check for checkmate or stalemate
        if analysis_board.is_checkmate():
            log_event('info', 'move_leads_to_checkmate', move=move_san)
            # Return a very high positive score for checkmate (good for the side that moved)
            return 9999
        elif analysis_board.is_stalemate():
            log_event('info', 'move_leads_to_stalemate', move=move_san)
            # Return a neutral score for stalemate (considered a draw)
            return 0

        # If it's a normal position, get the engine evaluation
        try:
            analysis = engine.analyse(board, Limit(depth=DEPTH), root_moves=[move])
            # Get the score object
            score_obj = analysis.get('score')
            if not score_obj:
                log_event('warning', 'no_score_for_move', move=move_san)
                return 0

            # Convert score to integer using mate_score to handle mate scores
            score = score_obj.pov(board.turn).score(mate_score=10000)
            # If score is None (unlikely), use 0
            if score is None:
                log_event('warning', 'null_score_for_move', move=move_san)
                return 0

            log_event('debug', 'move_score_obtained', move=move_san, score=score)
            return score

        except Exception as e:
            log_event('error', 'engine_analysis_error', move=move_san, error=str(e))
            # Return a neutral score on error to avoid breaking the analysis
            return 0

    except Exception as e:
        log_event('error', 'move_execution_error', move=move_san, error=str(e))
        # Return a neutral score on error to avoid breaking the analysis
        return 0


def get_all_move_ratings(board: Board) -> Dict[str, Dict]:
    """
    Return ratings for all legal moves on `board`.

    Returns a dictionary where:
    - Keys are move strings in SAN notation
    - Values are dictionaries containing:
      - "score": Raw engine score
      - "percentile": Percentile rank compared to best move (0-100)
      - "move": Move in SAN notation
      - "is_best_move": Whether this is the best move
    """
    # Log start of ratings calculation
    log_event('info', 'all_moves_analysis_start', fen=board.fen())

    # Check if there are legal moves
    legal_move_count = sum(1 for _ in board.legal_moves)
    if legal_move_count == 0:
        log_event('warning', 'no_legal_moves', fen=board.fen())
        return {}

    # Get all moves with scores
    move_scores: List[Tuple[str, int]] = []
    log_event('debug', 'processing_legal_moves', count=legal_move_count)

    # Initialize a counter to track progress
    move_count = 0
    successful_moves = 0

    for move in board.legal_moves:
        move_count += 1
        try:
            san = board.san(move)
            log_event('debug', 'analyzing_move', move=san, progress=f"{move_count}/{legal_move_count}")
            score = get_move_rating(board, move)
            move_scores.append((san, score))
            successful_moves += 1
            log_event('debug', 'move_analyzed', move=san, score=score, analyzed_count=successful_moves)
        except Exception as e:
            log_event('error', 'move_analysis_failed', move=str(move), error=str(e))
            # Continue with other moves

    # Check if we got any valid move scores
    if not move_scores:
        log_event('error', 'no_valid_move_scores')
        # Return an empty dictionary
        return {}

    # Sort moves by score (highest to lowest)
    sorted_moves = sorted(move_scores, key=lambda x: -x[1])
    log_event('debug', 'moves_sorted', count=len(sorted_moves))

    # Get best and worst scores
    best_score = sorted_moves[0][1]
    worst_score = sorted_moves[-1][1]
    score_range = max(1, best_score - worst_score)  # Avoid division by zero
    log_event('debug', 'score_range_calculated', best_score=best_score, worst_score=worst_score, range=score_range)

    # Identify the best move (highest score)
    best_move_san = sorted_moves[0][0]
    log_event('info', 'best_move_identified', move=best_move_san, score=best_score)

    # Calculate percentiles
    result = {}
    for san, score in sorted_moves:
        # If score matches the best score, it's 100%
        if score == best_score:
            percentile = 100
        else:
            # Normalize to 0-100 scale
            percentile = int(((score - worst_score) / score_range) * 100)

        # Include move in the result for consistency with top_moves format
        result[san] = {
            "move": san,  # Add move string here for consistency
            "score": score,
            "percentile": percentile,
            "is_best_move": (san == best_move_san)  # Mark if this is the best move
        }
        log_event('debug', 'move_rating_finalized', move=san, score=score, percentile=percentile, is_best=san == best_move_san)

    # Verify we have at least one result
    if not result:
        log_event('warning', 'empty_result_dictionary')

        # Create a fallback entry if needed
        if sorted_moves:
            first_move = sorted_moves[0][0]
            result[first_move] = {
                "move": first_move,
                "score": sorted_moves[0][1],
                "percentile": 100,
                "is_best_move": True
            }
            log_event('info', 'fallback_entry_added', move=first_move)

    log_event('info', 'all_moves_analysis_complete', move_count=len(result))
    return result


def analyze_move(board: Board, move_san: str) -> Dict:
    """
    Analyze a specific move on the given board.

    Returns a dictionary with:
    - "move": The move in SAN notation
    - "score": Raw engine score
    - "percentile": Percentile rank compared to best move (0-100)
    - "is_best_move": Boolean, true if move is the engine's top choice
    """
    # Log analysis start
    log_event('info', 'analyze_move_start', move=move_san, fen=board.fen())

    try:
        # First, check if the move is valid for this position
        try:
            # Try to make the move to see if it's legal
            test_board = board.copy()
            chess_move = None

            # Try to find the move in legal moves
            for m in test_board.legal_moves:
                if test_board.san(m) == move_san:
                    chess_move = m
                    break

            if chess_move is None:
                log_event('warning', 'invalid_move', move=move_san, valid_moves=[board.san(m) for m in board.legal_moves])
                return {
                    "error": "Invalid move",
                    "valid_moves": [board.san(m) for m in board.legal_moves]
                }

            # Get a quick solo evaluation for this move
            solo_score = get_move_rating(board, chess_move)
            log_event('debug', 'individual_score_obtained', move=move_san, score=solo_score)

            # For percentile calculation, we need all moves
            all_ratings = get_all_move_ratings(board)

            # If all_ratings is empty (which shouldn't happen), create a basic entry
            if not all_ratings:
                log_event('warning', 'no_move_ratings', move=move_san)
                return {
                    "move": move_san,
                    "score": solo_score,
                    "percentile": 50, # Default to middle percentile
                    "is_best_move": False
                }

            # Check if the requested move is in the ratings
            if move_san not in all_ratings:
                log_event('warning', 'move_missing_from_ratings', move=move_san)
                # Add it manually
                all_scores = [rating["score"] for rating in all_ratings.values()]
                if all_scores:
                    best_score = max(all_scores)
                    worst_score = min(all_scores)
                    score_range = max(1, best_score - worst_score)

                    # Calculate percentile
                    if solo_score >= best_score:
                        percentile = 100
                        is_best = True
                    else:
                        percentile = int(((solo_score - worst_score) / score_range) * 100)
                        is_best = False

                    result = {
                        "move": move_san,
                        "score": solo_score,
                        "percentile": percentile,
                        "is_best_move": is_best
                    }
                    log_event('info', 'manual_percentile_calculated', move=move_san, percentile=percentile, is_best=is_best)
                    return result
                else:
                    # Fallback if we can't calculate percentile
                    log_event('warning', 'using_fallback_percentile', move=move_san)
                    return {
                        "move": move_san,
                        "score": solo_score,
                        "percentile": 50,
                        "is_best_move": False
                    }

            # Get the move's data from all_ratings
            move_data = all_ratings[move_san]

            # Find best move score for double-checking is_best_move
            try:
                best_move = max(all_ratings.items(), key=lambda x: x[1]["score"])
                # Update is_best_move just to be sure
                move_data["is_best_move"] = (move_san == best_move[0])
                log_event('debug', 'best_move_verified', best_move=best_move[0], is_best=move_san == best_move[0])
            except Exception as e:
                log_event('error', 'best_move_verification_failed', error=str(e))
                # Keep existing is_best_move value

            # Make a deep copy to avoid any reference issues
            final_result = {
                "move": move_san,
                "score": move_data["score"],
                "percentile": move_data["percentile"],
                "is_best_move": move_data["is_best_move"]
            }

            log_event('info', 'analysis_complete', move=move_san, result=final_result)
            return final_result

        except Exception as e:
            log_event('error', 'move_processing_error', move=move_san, error=str(e))
            # Fallback - try to create a basic result
            return {
                "move": move_san,
                "score": 0,
                "percentile": 50,
                "is_best_move": False
            }

    except Exception as e:
        log_event('error', 'critical_analysis_error', move=move_san, error=str(e))
        # Return a very basic result to avoid breaking the API
        return {
            "move": move_san,
            "score": 0,
            "percentile": 50,
            "is_best_move": False
        }


def move_analysis_route(event, context=None):
    """
    Handler of AWS Lambda call for analyzing a specific move.

    Required parameters:
    - fen: Board position in FEN notation
    - move: Move to analyze in SAN notation

    Optional parameters:
    - enhanced: if 'true', returns detailed analysis data in same format as top_moves

    Returns:
    - Analysis result with score and percentile
    - 400 if parameters are invalid
    """
    try:
        data = event['queryStringParameters']
        log_event('info', 'move_analysis_request_received', params=data)

        try:
            fen = data['fen']
            move_san = data['move']
            # Check if enhanced format is requested (similar to top_moves endpoint)
            enhanced = data.get('enhanced', 'false').lower() == 'true'

            # Log parameters
            log_event('debug', 'move_analysis_parameters', fen=fen, move=move_san, enhanced=enhanced)

            board = Board(fen)
            log_event('debug', 'board_initialized', valid=board.is_valid(), legal_move_count=sum(1 for _ in board.legal_moves))
        except Exception as e:
            log_event('error', 'invalid_parameters', error=str(e))
            return {
                'statusCode': 400,
                'body': json.dumps({
                    "error": "Argument error",
                    "message": str(e)
                })
            }

        # Analyze the move with error handling
        try:
            analysis = analyze_move(board, move_san)

            # If there was an error, return it with 400 status
            if "error" in analysis:
                log_event('warning', 'move_analysis_failed', error=analysis['error'])
                return {
                    'statusCode': 400,
                    'body': json.dumps(analysis)
                }

            # Ensure all required fields exist
            if 'move' not in analysis:
                analysis['move'] = move_san
                log_event('warning', 'missing_move_field_added', move=move_san)

            if 'percentile' not in analysis:
                analysis['percentile'] = 50
                log_event('warning', 'missing_percentile_field_added')

            if 'score' not in analysis:
                analysis['score'] = 0
                log_event('warning', 'missing_score_field_added')

            if 'is_best_move' not in analysis:
                analysis['is_best_move'] = False
                log_event('warning', 'missing_is_best_move_field_added')

            log_event('info', 'move_analysis_successful', move=move_san, result=analysis)

            return {
                'statusCode': 200,
                'body': json.dumps({
                    "message": "SUCCESS",
                    "data": analysis
                })
            }
        except Exception as e:
            log_event('error', 'analysis_execution_failed', error=str(e))
            # Return a fallback analysis with reasonable defaults
            fallback_analysis = {
                "move": move_san,
                "score": 0,
                "percentile": 50,
                "is_best_move": False
            }
            log_event('warning', 'using_fallback_analysis', move=move_san)
            return {
                'statusCode': 200,  # Return 200 with fallback data to prevent frontend errors
                'body': json.dumps({
                    "message": "SUCCESS",
                    "data": fallback_analysis
                })
            }
    except Exception as e:
        log_event('error', 'unhandled_error', error=str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({
                "error": "Internal server error",
                "message": str(e)
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
    try:
        data = event['queryStringParameters']
        log_event('info', 'all_moves_analysis_request_received', params=data)

        try:
            fen = data.get('fen')
            log_event('debug', 'processing_fen', fen=fen)
            board = Board(fen)
            log_event('debug', 'board_initialized', valid=board.is_valid(), legal_move_count=sum(1 for _ in board.legal_moves))
        except Exception as e:
            log_event('error', 'invalid_fen_parameter', error=str(e), fen=data.get('fen'))
            return {
                'statusCode': 400,
                'body': json.dumps({
                    "error": "Argument error",
                    "message": str(e)
                })
            }

        log_event('info', 'starting_all_moves_analysis')
        all_ratings = get_all_move_ratings(board)
        log_event('info', 'all_moves_analysis_complete', move_count=len(all_ratings))

        return {
            'statusCode': 200,
            'body': json.dumps({
                "message": "SUCCESS",
                "data": all_ratings
            })
        }
    except Exception as e:
        log_event('error', 'all_moves_analysis_failed', error=str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({
                "error": "Internal server error",
                "message": str(e)
            })
        }


def handler(event, context):
    log_event('info', 'lambda_handler_invoked')
    return move_analysis_route(event, context)

# --- Local‑dev server (optional) ---------------------------
if __name__ == "__main__" and environ.get("LOCAL_DEV") == "true":
    from flask import Flask, request
    import threading

    lock = threading.Lock()
    app = Flask(__name__)

    @app.route("/predict", methods=["POST"])
    def predict_route():
        try:
            request_json = request.get_json(force=True)
            data = request_json.get("queryStringParameters", {})
            log_event('info', 'predict_endpoint_request', request=request_json)

            # Validate required fields
            if not data.get('fen') or not data.get('move'):
                log_event('error', 'missing_required_fields', received_keys=list(data.keys()))
                return {"statusCode": 400, "body": json.dumps({"error": "Missing required fields. Required: fen, move."})}

            with lock:
                # Build proper event structure
                event = {"queryStringParameters": data}
                log_event('debug', 'invoking_move_analysis')
                response = move_analysis_route(event)

                # Verify the response structure is correct
                if response and response.get('body'):
                    try:
                        body_data = json.loads(response['body'])
                        if not body_data.get('data'):
                            log_event('warning', 'response_missing_data_field', body=body_data)
                    except Exception as e:
                        log_event('error', 'response_parsing_failed', error=str(e))

                log_event('info', 'predict_endpoint_response', status_code=response.get('statusCode'))
                return response
        except Exception as e:
            log_event('error', 'predict_endpoint_critical_error', error=str(e))
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Internal server error", "message": str(e)})
            }

    # Warm the engine for faster local calls
    get_engine()
    log_event('info', 'local_dev_server_starting', port=8080, depth=DEPTH)
    app.run(host="0.0.0.0", port=8080, threaded=False)