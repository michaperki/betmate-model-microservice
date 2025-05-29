#!/bin/bash

echo "Testing move analysis endpoint directly..."
curl -X POST http://localhost:8081/predict \
  -H "Content-Type: application/json" \
  -d '{
    "queryStringParameters": {
      "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
      "move": "e4",
      "enhanced": "true"
    }
  }' | python -m json.tool

echo -e "\n\nTesting top moves endpoint for comparison..."
curl -X POST http://localhost:8082/predict \
  -H "Content-Type: application/json" \
  -d '{
    "queryStringParameters": {
      "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
      "n": "3",
      "enhanced": "true"
    }
  }' | python -m json.tool

echo -e "\n\nTesting wdl endpoint for comparison..."
curl -X POST http://localhost:8083/predict \
  -H "Content-Type: application/json" \
  -d '{
    "queryStringParameters": {
      "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
      "white_time": "300",
      "black_time": "300"
    }
  }' | python -m json.tool