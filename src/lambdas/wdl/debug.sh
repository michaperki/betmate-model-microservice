#!/bin/bash
# Script to debug Stockfish in the container

echo "Checking Stockfish locations"
echo "--------------------------"
if [ -f "/usr/games/stockfish" ]; then
  echo "✅ /usr/games/stockfish exists"
  ls -l /usr/games/stockfish
else
  echo "❌ /usr/games/stockfish does not exist"
fi

if [ -f "./assets/stockfish_linux" ]; then
  echo "✅ ./assets/stockfish_linux exists"
  ls -l ./assets/stockfish_linux
else
  echo "❌ ./assets/stockfish_linux does not exist"
fi

echo
echo "Checking Stockfish executability"
echo "--------------------------"
if [ -f "/usr/games/stockfish" ]; then
  if [ -x "/usr/games/stockfish" ]; then
    echo "✅ /usr/games/stockfish is executable"
  else
    echo "❌ /usr/games/stockfish is not executable"
  fi
fi

if [ -f "./assets/stockfish_linux" ]; then
  if [ -x "./assets/stockfish_linux" ]; then
    echo "✅ ./assets/stockfish_linux is executable"
  else
    echo "❌ ./assets/stockfish_linux is not executable"
  fi
fi

echo
echo "Checking environment variables"
echo "--------------------------"
echo "STOCKFISH_PATH = ${STOCKFISH_PATH:-not set}"

echo
echo "Trying to run Stockfish"
echo "--------------------------"
if [ -f "/usr/games/stockfish" ]; then
  echo "Trying to run /usr/games/stockfish (will timeout after 2s):"
  timeout 2s /usr/games/stockfish || echo "Stockfish terminated (expected)"
fi

if [ -f "./assets/stockfish_linux" ]; then
  echo "Trying to run ./assets/stockfish_linux (will timeout after 2s):"
  timeout 2s ./assets/stockfish_linux || echo "Stockfish terminated (expected)"
fi

echo
echo "Python check"
echo "--------------------------"
python -c "
import chess.engine
import os
import sys

print(f'Python version: {sys.version}')
print(f'Current directory: {os.getcwd()}')

stockfish_path = os.environ.get('STOCKFISH_PATH', '/usr/games/stockfish')
print(f'Using stockfish path: {stockfish_path}')

try:
    print('Attempting to create engine...')
    engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
    print('✅ Engine successfully created')
    engine.close()
except Exception as e:
    print(f'❌ Error creating engine: {e}')
    
    # Try the bundled binary as fallback
    try:
        print('Trying bundled binary as fallback...')
        engine = chess.engine.SimpleEngine.popen_uci('./assets/stockfish_linux')
        print('✅ Engine successfully created with bundled binary')
        engine.close()
    except Exception as e2:
        print(f'❌ Error with bundled binary: {e2}')
"