#!/bin/bash
set -e

echo "Rebuilding and testing WDL container"
echo "===================================="

cd "$(dirname "$0")"
echo "Working directory: $(pwd)"

# Make debug script executable
chmod +x ./src/lambdas/wdl/debug.sh

# Rebuild the container
echo "Rebuilding container..."
docker-compose build wdl-container

# Stop existing containers if running
docker-compose stop wdl-container || true

# Start container
echo "Starting container..."
docker-compose up -d wdl-container

# Wait for container to start
sleep 2

# Get container ID
CONTAINER_ID=$(docker-compose ps -q wdl-container)
if [ -z "$CONTAINER_ID" ]; then
    echo "❌ Failed to get container ID"
    exit 1
fi

echo "Container ID: $CONTAINER_ID"

# Copy debug script to container
echo "Running debug script inside container..."
docker exec -it $CONTAINER_ID bash -c "cd /app && ./debug.sh"

# Test API
echo
echo "Testing API endpoint..."
curl -X POST http://localhost:8004/predict \
  -H "Content-Type: application/json" \
  -d '{"queryStringParameters":{"fen":"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1","white_time":180,"black_time":180}}' | jq .

echo
echo "Debugging completed!"