import pytest

from src import wdl_engine, top_moves_engine


@pytest.fixture(scope='session', autouse=True)
def cleanup(request):
    """Close engines after testing is complete"""
    def close_engine():
        wdl_engine.close()
        top_moves_engine.close()
    request.addfinalizer(close_engine)
