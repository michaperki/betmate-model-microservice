#!/bin/bash
echo "Stopping any running containers..."
docker compose down

echo "Building containers with updated code..."
docker compose build

echo "Starting containers..."
docker compose up