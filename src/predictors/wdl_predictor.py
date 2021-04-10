import numpy as np
import os
import math
import chess.engine
from chess import Board
from chess.engine import SimpleEngine
from pydantic import BaseModel


class WDLResponse(BaseModel):
    white_win: float
    draw: float
    black_win: float


def get_wdl_predictor(engine: SimpleEngine, time_limit=0.1):

    print('initializing wdl model')

    TIME_LIMIT = time_limit

    get_file = lambda f: os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, f)

    with open(get_file('assets/black_win_fraction.npy'), 'rb') as f:
        bwf = np.load(f)
    with open(get_file('assets/white_win_fraction.npy'), 'rb') as f:
        wwf = np.load(f)
    with open(get_file('assets/draw_fraction.npy'), 'rb') as f:
        df = np.load(f)

    def predict(board: Board, white_time: int, black_time: int):

        win_bin: int = _get_win_bin(board)

        white_time = min(180, max(1, white_time))
        black_time = min(180, max(1, black_time))

        return WDLResponse(
            white_win=wwf[white_time, black_time, win_bin],
            draw=df[white_time, black_time, win_bin],
            black_win=bwf[white_time, black_time, win_bin]
        )

    def _get_win_bin(board: Board):

        info = engine.analyse(board, chess.engine.Limit(time=TIME_LIMIT))
        eval = info['score'].white().score(mate_score=1000)
        pwin = 1 / (1 + math.pow(10, -eval / 400))

        if pwin < 0.10:
            indexOnWinBin = 0
        elif pwin >= 0.10 and pwin < 0.40:
            indexOnWinBin = 1
        elif pwin >= 0.40 and pwin < 0.60:
            indexOnWinBin = 2
        elif pwin >= 0.60 and pwin < 0.90:
            indexOnWinBin = 3
        elif pwin >= 0.00:
            indexOnWinBin = 4

        return indexOnWinBin

    return predict
