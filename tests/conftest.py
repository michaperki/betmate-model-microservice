import pytest

from src import app, engine


@pytest.fixture
def client():
    return app.test_client()

@pytest.fixture(scope='session', autouse=True)
def cleanup(request):
    def close_engine():
        engine.close()
    request.addfinalizer(close_engine)
