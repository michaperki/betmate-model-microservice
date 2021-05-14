import random
import chess


def generate_chess_game():
    random.seed()
    game = chess.Board()
    white_time = 180
    black_time = 180
    move_counter = 30
    while not game.is_game_over() and move_counter > 0:
        move = random.choice(list(game.generate_legal_moves()))

        if game.turn == chess.WHITE:
            white_time -= random.randint(1, 10)
            white_time = max(white_time, 10)
        else:
            black_time -= random.randint(1, 10)
            black_time = max(black_time, 10)

        game.push(move)
        move_counter -= 1
        yield game.fen(), white_time, black_time


def get_bad_fen_list():
    return [
        'rnbqkbnr/pppppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3',
        'rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/PPP2PPP/RNBQKBNR w KQkq - 0 3',
        'rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR KQkq - 0 3',
        'rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq 0 3',
        'rnbqknr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3',
        'rnbqkbnr/ppp2ppp/4p3/3p4/PPP2PPP/RNBQKBNR w KQkq - 0 3',
        'rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8//PPP2PPP/RNBQKBNR w KQkq - 0 3',
        'rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPX/RNBQKBNR w KQkq - 0 3',
        'rnbqkbnr/ppp2pjb/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3',
    ]
