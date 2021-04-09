import numpy as np
import os
import math
import chess.engine
from chess import Board


def get_wdl_predictor(time_limit=0.1):

    TIME_LIMIT = time_limit

    with open(os.path.join(os.getcwd(), 'assets/black_win_fraction.npy'), 'rb') as f:
        bwf = np.load(f)
    with open(os.path.join(os.getcwd(), 'assets/white_win_fraction.npy'), 'rb') as f:
        wwf = np.load(f)
    with open(os.path.join(os.getcwd(), 'assets/draw_fraction.npy'), 'rb') as f:
        df = np.load(f)

    engine = chess.engine.SimpleEngine.popen_uci(os.path.join(os.getcwd(), 'assets/stockfish'))
    engine.configure({"Threads": os.cpu_count() - 1})
    engine.configure({"Hash": 1024})

    def predict(board: Board, white_time: int, black_time: int):


        win_bin: int = _get_win_bin(board)

        return {
            'white_win': wwf[white_time, black_time, win_bin],
            'draw': df[white_time, black_time, win_bin],
            'black_win': bwf[white_time, black_time, win_bin],
        }

    def _get_win_bin(board: Board) -> int:
        info = engine.analyse(board, chess.engine.Limit(time=TIME_LIMIT))
        eval = info['score'].white().score(mate_score=1000)
        pwin = 1/(1+math.pow(10,-eval/400))

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


