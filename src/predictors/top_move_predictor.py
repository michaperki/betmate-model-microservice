from typing import List
from chess.engine import Limit, SimpleEngine
from chess import Board, Move

def get_top_move_predictor(engine: SimpleEngine, depth=12):

    print('initializing top move model')

    DEPTH = depth

    desc = lambda x: -x[1]

    def _get_move_rating(board: Board, move: Move):
        analysis = engine.analyse(board, Limit(depth=DEPTH), root_moves=[move])
        return analysis.get('score').pov(board.turn).score()

    def predict(board: Board, n: int) -> List[str]:
        move_scores = [(str(move), _get_move_rating(board, move))
                        for move in board.legal_moves]
        
        return [move for move, _ in sorted(move_scores, key=desc)[:n]]

    return predict
