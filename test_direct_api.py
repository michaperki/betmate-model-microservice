import requests
import json

# Test a specific position and move
fen = "r1b1kbnr/pppp1p1p/2n2qp1/4p1Q1/2B1P3/5N2/PPPP1PPP/RNB1K2R b KQkq - 1 5"
move_to_test = "Qxg5"

print(f"Testing position: {fen}")
print(f"Testing move: {move_to_test}")

# Test the move analysis microservice directly
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

# Test with the router
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

# Test a modified move format (try with and without the 'x')
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

# Test with Qf6xg5 (full move specification)
print("\n--- Testing with full move: Qf6xg5 ---")

try:
    response = requests.post(
        "http://localhost:8083/predict", 
        json={
            "queryStringParameters": {
                "fen": fen,
                "move": "Qf6xg5",
                "enhanced": "true"
            }
        }
    )
    
    print(f"Status code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))
    
except Exception as e:
    print(f"Error testing microservice with full move: {e}")