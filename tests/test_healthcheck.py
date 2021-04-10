from flask.testing import FlaskClient
from flask.wrappers import Response

def test_base(client: FlaskClient):
    response: Response = client.get('/')
    assert response.status_code == 200
    # data = json.loads(response.data)
    # assert data['message'] == "SUCCESS"

def test_hc(client: FlaskClient):
    response: Response = client.get('/healthcheck')
    assert response.status_code == 200

def test_unfound(client: FlaskClient):
    response: Response = client.get('/asdf')
    assert response.status_code == 404
