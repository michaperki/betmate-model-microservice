
FROM python:3.10-slim

RUN apt-get update && apt-get install -y gcc python3-dev stockfish && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# Ensure binary is executable
RUN chmod +x ./assets/stockfish_linux

# Set environment variable for Stockfish path
ENV STOCKFISH_PATH=/usr/games/stockfish

CMD ["python", "top_moves.py"]
