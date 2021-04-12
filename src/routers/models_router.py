
import os
from chess import Board
from src.predictors.wdl_predictor import WDLResponse, get_wdl_predictor
from flask import request
from src import app, engine
from src.services.format_response import formatSuccess, formatError


@app.route('/models/wdl', methods=['GET'])
def wdl(model=get_wdl_predictor(engine)):

    try:
        board = Board(request.args.get('fen'))
        white_time: int = int(request.args.get('white_time'))
        black_time: int = int(request.args.get('black_time'))
    except Exception as e:
        return formatError(400, str(e), "Argument error")

    probabilities: WDLResponse = model(board, white_time, black_time)

    return formatSuccess(probabilities.dict())


@app.route('/models/move', methods=['GET'])
def move():
    return formatError(500, "Endpoint not yet implemented", "NotImplementedError")
