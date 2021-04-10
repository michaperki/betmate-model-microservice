from flask import jsonify


def formatSuccess(payload={}):
    return jsonify({
        "code": 200,
        "message": "SUCCESS",
        "data": payload
    })


def formatError(code=500, message="", error={}):
    return jsonify({
        "code": code,
        "message": message if len(message) > 0 else "ERROR",
        "error": error
    })
