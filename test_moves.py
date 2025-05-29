from chess import Board
import requests
import json

# Test a specific position and move
fen = "r1b1kbnr/pppp1p1p/2n2qp1/4p1Q1/2B1P3/5N2/PPPP1PPP/RNB1K2R b KQkq - 1 5"
move_to_test = "Qxg5"

print(f"Testing position: {fen}")
print(f"Testing move: {move_to_test}")

# 1. Check if the move is legal using python-chess
board = Board(fen)

# Get all legal moves in UCI and SAN formats
legal_uci = [move.uci() for move in board.legal_moves]
legal_san = []

for move in board.legal_moves:
    try:
        san = board.san(move)
        legal_san.append(san)
    except Exception as e:
        print(f"Error getting SAN for move {move}: {e}")

print("\nLegal moves in UCI format:", legal_uci)
print("Legal moves in SAN format:", legal_san)

# Try to execute the move
is_move_legal = False
matching_moves = []

for move in board.legal_moves:
    try:
        san = board.san(move)
        if san == move_to_test:
            is_move_legal = True
            matching_moves.append((move.uci(), san))
        # Also check if move without check/mate marker matches
        elif san.replace('+', '').replace('#', '') == move_to_test.replace('+', '').replace('#', ''):
            matching_moves.append((move.uci(), san))
    except Exception as e:
        print(f"Error processing move {move}: {e}")

print(f"\nIs {move_to_test} a legal move? {is_move_legal}")
if matching_moves:
    print(f"Matching moves (UCI, SAN): {matching_moves}")

# 2. Test the move analysis microservice directly
try:
    print("\n--- Testing microservice directly ---")
    response = requests.post(
        "http://localhost:8083/predict", 
        json={
            "queryStringParameters": {
                "fen": fen,
                "move": move_to_test,
                "enhanced": "true"
            }
        }
    )
    
    print(f"Status code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))
    
except Exception as e:
    print(f"Error testing microservice: {e}")

# 3. Test with the router
try:
    print("\n--- Testing through router ---")
    response = requests.get(
        f"http://localhost:8000/dev/move-analysis?fen={requests.utils.quote(fen)}&move={move_to_test}&enhanced=true"
    )
    
    print(f"Status code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))
    
except Exception as e:
    print(f"Error testing router: {e}")

# 4. Test a modified move format (try with and without the 'x')
if 'x' in move_to_test:
    move_without_x = move_to_test.replace('x', '')
    print(f"\n--- Testing with modified move (without 'x'): {move_without_x} ---")
    
    try:
        response = requests.post(
            "http://localhost:8083/predict", 
            json={
                "queryStringParameters": {
                    "fen": fen,
                    "move": move_without_x,
                    "enhanced": "true"
                }
            }
        )
        
        print(f"Status code: {response.status_code}")
        print("Response:")
        print(json.dumps(response.json(), indent=2))
        
    except Exception as e:
        print(f"Error testing microservice with modified move: {e}")