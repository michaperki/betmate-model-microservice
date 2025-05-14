FROM python:3.8-slim

WORKDIR /app

# Install dependencies with exact versions to avoid compatibility issues
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create assets directory
RUN mkdir -p /app/assets

# Copy function code and entrypoint
COPY move_analysis.py .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Expose port
EXPOSE 8080

# Copy Stockfish engine - We'll mount this at runtime
CMD ["./entrypoint.sh"]