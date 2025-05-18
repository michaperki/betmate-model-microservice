
FROM python:3.10-slim

# Install stockfish and development tools
RUN apt-get update && apt-get install -y gcc python3-dev stockfish && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# Ensure both stockfish binaries are executable
RUN chmod +x ./assets/stockfish_linux && \
    echo "Checking stockfish installation..." && \
    ls -la /usr/games/stockfish || echo "System stockfish not found at expected location" && \
    ls -la ./assets/stockfish_linux

# Try symlink if system stockfish is missing
RUN if [ ! -f "/usr/games/stockfish" ]; then \
      mkdir -p /usr/games && \
      ln -s $(pwd)/assets/stockfish_linux /usr/games/stockfish && \
      chmod +x /usr/games/stockfish; \
    fi

# Set environment variable for Stockfish path with fallback
ENV STOCKFISH_PATH=/usr/games/stockfish

# Create a simple test to verify installation
RUN echo "#!/bin/bash\necho 'Testing stockfish installation'\nif [ -f /usr/games/stockfish ]; then echo '/usr/games/stockfish exists'; else echo '/usr/games/stockfish missing'; fi" > /test-stockfish.sh && \
    chmod +x /test-stockfish.sh && \
    /test-stockfish.sh

CMD ["python", "wdl.py"]
