import json
import os
from flask import Flask
from src.services.format_response import formatSuccess

app = Flask(__name__)

from src import *
from src.routers import *

if __name__ == '__main__':
    app.run(port=int(os.environ.get('PORT', 5000)))

@app.route('/')
def init():
    return formatSuccess()
