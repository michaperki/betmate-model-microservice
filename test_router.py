import requests
import json

# Test the router for move analysis
test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
test_move = "e4"

print(f"Testing move analysis through router for FEN: {test_fen}")
print(f"Move to analyze: {test_move}")

# Test direct call to move-analysis microservice
try:
    direct_response = requests.post(
        "http://localhost:8083/predict",  # Direct to move-analysis
        json={
            "queryStringParameters": {
                "fen": test_fen,
                "move": test_move,
                "enhanced": "true"
            }
        }
    )
    
    print(f"Direct call status: {direct_response.status_code}")
    direct_result = direct_response.json()
    direct_body = json.loads(direct_result["body"])
    print(f"Direct call data: {direct_body.get('data')}")
    
    # Now test through router
    router_response = requests.get(
        f"http://localhost:8000/dev/move-analysis?fen={test_fen}&move={test_move}&enhanced=true"
    )
    
    print(f"Router call status: {router_response.status_code}")
    router_body = router_response.json()
    print(f"Router call data: {router_body.get('data')}")
    
    # Compare responses
    direct_data = direct_body.get('data')
    router_data = router_body.get('data')
    
    if direct_data and router_data:
        print("\nComparison:")
        if direct_data == router_data:
            print("✅ Both responses match!")
        else:
            print("❌ Responses are different:")
            print(f"Direct: {direct_data}")
            print(f"Router: {router_data}")
    
except Exception as e:
    print(f"Error testing router: {e}")