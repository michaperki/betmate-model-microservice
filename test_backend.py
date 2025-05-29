import requests
import json
import urllib.parse

# Test a specific position and move
fen = "r1b1kbnr/pppp1p1p/2n2qp1/4p1Q1/2B1P3/5N2/PPPP1PPP/RNB1K2R b KQkq - 1 5"
move_to_test = "Qxg5"

print(f"Testing position: {fen}")
print(f"Testing move: {move_to_test}")

# Try to connect to the backend
try:
    print("\n--- Testing backend directly ---")
    url = f"http://localhost:9090/analysis/move?fen={urllib.parse.quote(fen)}&move={move_to_test}"
    print(f"URL: {url}")
    
    response = requests.get(url)
    
    print(f"Status code: {response.status_code}")
    if response.status_code == 200:
        print("Response:")
        print(json.dumps(response.json(), indent=2))
    else:
        print("Response text:")
        print(response.text)
    
except Exception as e:
    print(f"Error testing backend: {e}")