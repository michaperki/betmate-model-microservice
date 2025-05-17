FROM python:3.8-slim

WORKDIR /app

# Install dependencies with exact versions to avoid compatibility issues
COPY requirements.txt .
RUN apt-get update && apt-get install -y stockfish && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt

# Create assets directory
RUN mkdir -p /app/assets

# Copy function code and entrypoint
COPY move_analysis.py .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Set environment variable for Stockfish path
ENV STOCKFISH_PATH=/usr/games/stockfish

# Expose port
EXPOSE 8080

CMD ["./entrypoint.sh"]