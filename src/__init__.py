import os
from flask import Flask
from src.services.format_response import formatSuccess
from chess.engine import SimpleEngine

app = Flask(__name__)

engine = SimpleEngine.popen_uci(os.path.join(os.getcwd(), 'assets/stockfish'))
# engine.configure({"Threads": os.cpu_count() - 1})
# engine.configure({"Hash": 1024})

import src.routers  # noqa: E402

# if __name__ == '__main__':
#     app.run(port=int(os.environ.get('PORT', 5000)))

@app.route('/')
def init():
    return formatSuccess()

