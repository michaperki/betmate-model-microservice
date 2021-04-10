from flask import jsonify


def formatSuccess(payload={}):
    return jsonify({
        "message": "SUCCESS",
        "data": payload
    }), 200


def formatError(code=500, message="", error={}):
    return jsonify({
        "message": message if len(message) > 0 else "ERROR",
        "error": error
    }), code
