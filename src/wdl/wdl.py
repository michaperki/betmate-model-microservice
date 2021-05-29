from chess import Board
from chess.engine import SimpleEngine, Limit
from numpy import load
from math import pow
import json
from os import environ
from sys import platform

TIME_LIMIT = float(environ.get('TIME_LIMIT', 0.1))
HASH_SIZE = int(environ.get('HASH_SIZE', 256))

executable = f'stockfish_{"mac" if platform == "darwin" else "linux"}'
engine = SimpleEngine.popen_uci(f'./assets/{executable}')
engine.configure({"Hash": HASH_SIZE})

with open('./assets/black_win_fraction.npy', 'rb') as f:
    bwf = load(f)
with open('./assets/white_win_fraction.npy', 'rb') as f:
    wwf = load(f)
with open('./assets/draw_fraction.npy', 'rb') as f:
    df = load(f)


def get_win_bin(board):
    info = engine.analyse(board, Limit(time=TIME_LIMIT))
    eval = info['score'].white().score(mate_score=1000)
    pwin = 1 / (1 + pow(10, -eval / 400))

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


def model(board, white_time, black_time):
    win_bin: int = get_win_bin(board)

    white_time = min(180, max(1, white_time))
    black_time = min(180, max(1, black_time))

    return {
        'white_win': wwf[white_time, black_time, win_bin],
        'draw': df[white_time, black_time, win_bin],
        'black_win': bwf[white_time, black_time, win_bin]
    }


def wdl_route(event, context=None):
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
