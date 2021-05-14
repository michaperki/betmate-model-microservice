from flask.testing import FlaskClient
import chess
import random
import json
from urllib.parse import quote
from flask.wrappers import Response
from tests.helpers import generate_chess_game, get_bad_fen_list

def get_bad_n_list():
    return ['a', 'chess', None, [6], True, False, -10, 0]


def create_top_move_query(fen, n):
    return f'/models/top_moves?fen={quote(fen)}&n={n}'


def test_top_move_good(client: FlaskClient):
    for fen, _, _ in generate_chess_game():
        response: Response = client.get(create_top_move_query(fen, random.randint(3, 6)))
        assert response.status_code == 200
        data = json.loads(response.data)['data']
        assert type(data) == list
        assert len(data) >= 0


def test_top_move_bad_fen(client: FlaskClient):
    for bad_fen in get_bad_fen_list():
        response: Response = client.get(create_top_move_query(bad_fen, random.randint(3, 6)))
        assert response.status_code == 400


def test_top_move_bad_n(client: FlaskClient):
    fen = 'rnbqkbnr/ppp2ppp/4p3/8/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3'
    for bad_n in get_bad_n_list():
        response: Response = client.get(create_top_move_query(fen, bad_n))
        assert response.status_code == 400
