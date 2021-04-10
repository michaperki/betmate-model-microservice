import os
from flask import Flask
from src.services.format_response import formatSuccess

app = Flask(__name__)

import src.routers  # noqa: E402

if __name__ == '__main__':
    app.run(port=int(os.environ.get('PORT', 5000)))


@app.route('/')
def init():
    return formatSuccess()
