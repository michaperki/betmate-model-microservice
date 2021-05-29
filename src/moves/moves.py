from chess import Board
from chess.engine import SimpleEngine, Limit
import json
from os import environ

DEPTH = environ.get('DEPTH', 10)
HASH_SIZE = environ.get('HASH_SIZE', 256)

executable = "stockfish_linux"
engine = SimpleEngine.popen_uci(f'./assets/{executable}')
engine.configure({"Hash": HASH_SIZE})


def get_move_rating(board, move):
    analysis = engine.analyse(board, Limit(depth=DEPTH), root_moves=[move])
    return analysis.get('score').pov(board.turn).score(mate_score=1000)


def model(board, n):
    move_scores = [(board.san(move), get_move_rating(board, move))
                   for move in board.legal_moves]

    return [move for move, _ in sorted(move_scores, key=lambda x: -x[1])[:n]]


def moves_route(event, context):
    data = event['queryStringParameters']
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
