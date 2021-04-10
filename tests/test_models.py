from flask.testing import FlaskClient
import chess
import random
import json
from urllib.parse import quote

from flask.wrappers import Response

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
       'rnbqkbnr/ppp2pjb/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3' 
    ]

def get_bad_time_list():
    return [
        (180, 'a'),
        ('chess', 180),
        (180, None),
        (None, 180),
        ([180], 180),
        (True, 180),
        (180, False)
    ]

def create_wdl_query(fen, white_time, black_time):
    return f'/models/wdl?fen={quote(fen)}&white_time={white_time}&black_time={black_time}'

def test_wdl_good(client: FlaskClient):
    for fen, white_time, black_time in generate_chess_game():
        response: Response = client.get(create_wdl_query(fen, white_time, black_time))
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        assert data['black_win'] >= 0
        assert data['black_win'] <= 1
        assert data['draw'] >= 0
        assert data['draw'] <= 1
        assert data['white_win'] >= 0
        assert data['white_win'] <= 1

def test_wdl_bad_fen(client: FlaskClient):
    white_time, black_time = 180, 180

    for bad_fen in get_bad_fen_list():
        response: Response = client.get(create_wdl_query(bad_fen, white_time, black_time))
        assert response.status_code == 400


def test_wdl_bad_time(client: FlaskClient):
    fen = 'rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3'
    for white_time, black_time in get_bad_time_list():
        response: Response = client.get(create_wdl_query(fen, white_time, black_time))
        assert response.status_code == 400


def test_move_unimplemented(client: FlaskClient):
    response: Response = client.get('/models/move')
    assert response.status_code == 500
