#!/bin/bash
set -e

echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"
echo "Installed packages:"
pip list

echo "Testing imports..."
python -c "import flask; print('Flask import successful!')"
python -c "import werkzeug; print('Werkzeug import successful!')"
python -c "import chess; print('Chess import successful!')"

echo "Starting application..."
exec python move_analysis.py