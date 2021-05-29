import json

from src import wdl_route
from tests.helpers import generate_chess_game, get_bad_fen_list


def get_bad_time_list():
    return [
        (180, 'a'),
        ('chess', 180),
        (180, None),
        (None, 180),
        ([180], 180),
    ]


def create_wdl_query(fen, white_time, black_time):
    return {
        'queryStringParameters': {
            'fen': fen,
            'white_time': white_time,
            'black_time': black_time
        }
    }


def test_wdl_good():
    for fen, white_time, black_time in generate_chess_game():
        response = wdl_route(create_wdl_query(fen, white_time, black_time))
        assert response['statusCode'] == 200
        data = json.loads(response['body'])['data']
        assert data['black_win'] >= 0
        assert data['black_win'] <= 1
        assert data['draw'] >= 0
        assert data['draw'] <= 1
        assert data['white_win'] >= 0
        assert data['white_win'] <= 1


def test_wdl_bad_fen():
    white_time, black_time = 180, 180

    for bad_fen in get_bad_fen_list():
        response = wdl_route(create_wdl_query(bad_fen, white_time, black_time))
        assert response['statusCode'] == 400


def test_wdl_bad_time():
    fen = 'rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3'
    for white_time, black_time in get_bad_time_list():
        response = wdl_route(create_wdl_query(fen, white_time, black_time))
        assert response['statusCode'] == 400

