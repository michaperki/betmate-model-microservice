from flask import jsonify, request
from src import app
from src.services.format_response import formatSuccess, formatError

@app.route('/healthcheck', methods=['GET'])
def healthcheck():
    return formatSuccess()
