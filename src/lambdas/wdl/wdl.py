from typing import Dict
from chess import Board
from chess.engine import SimpleEngine, Limit
from numpy import load, ndarray
from math import pow
import json
from os import environ
from sys import platform

# Config
TIME_LIMIT = float(environ.get('TIME_LIMIT', 0.1))
HASH_SIZE = int(environ.get('HASH_SIZE', 256))

# Init Stockfish chess engine
executable = f'stockfish_{"mac" if platform == "darwin" else "linux"}'
engine = SimpleEngine.popen_uci(f'./assets/{executable}')
engine.configure({"Hash": HASH_SIZE})

# Load model
with open('./assets/black_win_fraction.npy', 'rb') as f:
    bwf: ndarray = load(f)
with open('./assets/white_win_fraction.npy', 'rb') as f:
    wwf: ndarray = load(f)
with open('./assets/draw_fraction.npy', 'rb') as f:
    df: ndarray = load(f)


def get_win_bin(board: Board) -> int:
    """Convert `board` state to 'bin' corresponding to 'white vs. black' favorability"""

    # Evaluate board
    info = engine.analyse(board, Limit(time=TIME_LIMIT))
    score = info['score'].white().score(mate_score=1000)

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
    win_bin: int = get_win_bin(board)

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

    app = Flask(__name__)

    @app.route("/predict", methods=["POST"])
    def route():
        return wdl_route({"queryStringParameters": request.get_json().get("queryStringParameters", {})})

    app.run(host="0.0.0.0", port=8080)
