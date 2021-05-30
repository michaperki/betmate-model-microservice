import random
import json

from src import top_moves_route
from tests.helpers import generate_chess_game, get_bad_fen_list


def get_bad_n_list():
    return ['a', 'chess', None, [6], False, -10, 0]


def create_top_move_query(fen: str, n: int):
    return {
        'queryStringParameters': {
            'fen': fen,
            'n': n
        }
    }


def test_top_move_good():
    for fen, _, _ in generate_chess_game():
        n = random.randint(3, 6)
        response = top_moves_route(create_top_move_query(fen, n))
        assert response['statusCode'] == 200
        data = json.loads(response['body'])['data']
        assert type(data) == list
        assert len(data) <= n


def test_top_move_bad_fen():
    for bad_fen in get_bad_fen_list():
        response = top_moves_route(create_top_move_query(bad_fen, random.randint(3, 6)))
        assert response['statusCode'] == 400


def test_top_move_bad_n():
    fen = 'rnbqkbnr/ppp2ppp/4p3/8/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3'
    for bad_n in get_bad_n_list():
        response = top_moves_route(create_top_move_query(fen, bad_n))
        assert response['statusCode'] == 400
