from os import cpu_count
from src.services.file_system_helpers import get_stockfish_executable_path
from flask import Flask
from src.services.format_response import formatSuccess
from chess.engine import SimpleEngine

app = Flask(__name__)

engine = SimpleEngine.popen_uci(get_stockfish_executable_path())
# engine.configure({"Threads": cpu_count() - 1})
# engine.configure({"Hash": 1024})

import src.routers  # noqa: E402


@app.route('/')
def init():
    return formatSuccess()
