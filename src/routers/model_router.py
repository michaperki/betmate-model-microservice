
from flask import jsonify, request
from src import app
from src.services.format_response import formatSuccess, formatError

@app.route('/models/wdl', methods=['GET'])
def wdl():
    return formatSuccess()

@app.route('/models/move', methods=['GET'])
def move():
    return formatSuccess()