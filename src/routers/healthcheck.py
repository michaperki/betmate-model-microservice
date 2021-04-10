from src import app
from src.services.format_response import formatSuccess


@app.route('/healthcheck', methods=['GET'])
def healthcheck():
    return formatSuccess()
