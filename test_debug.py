import requests
import json
import sys

# Test different endpoints to find where the issue is
test_fen = "r2r2k1/2q1np2/p3bbpp/1pp1p3/4P3/1PP1NNPP/P1Q2PB1/3RR1K1 w - - 0 19"
test_move = "c4"

def test_direct_microservice():
    """Test direct connection to the move analysis microservice"""
    print("\n*** Testing direct connection to move analysis microservice ***")
    try:
        url = "http://localhost:8083/predict"
        print(f"URL: {url}")
        
        response = requests.post(
            url,
            json={
                "queryStringParameters": {
                    "fen": test_fen,
                    "move": test_move,
                    "enhanced": "true"
                }
            }
        )
        
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            print("Response:")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error making request: {e}")
        return False

def test_router():
    """Test connection through the router"""
    print("\n*** Testing connection through router ***")
    try:
        url = f"http://localhost:8000/dev/move-analysis?fen={requests.utils.quote(test_fen)}&move={test_move}&enhanced=true"
        print(f"URL: {url}")
        
        response = requests.get(url)
        
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            print("Response:")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error making request: {e}")
        return False

def test_backend():
    """Test connection through the backend"""
    print("\n*** Testing connection through backend (if available) ***")
    try:
        url = f"http://localhost:9090/analysis/move?fen={requests.utils.quote(test_fen)}&move={test_move}"
        print(f"URL: {url}")
        
        response = requests.get(url)
        
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            print("Response:")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error making request: {e}")
        return False

if __name__ == "__main__":
    print(f"Testing move analysis for FEN: {test_fen}")
    print(f"Move to analyze: {test_move}")
    
    direct_result = test_direct_microservice()
    router_result = test_router()
    backend_result = test_backend()
    
    print("\n*** Summary ***")
    print(f"Direct microservice test: {'✅ PASS' if direct_result else '❌ FAIL'}")
    print(f"Router test: {'✅ PASS' if router_result else '❌ FAIL'}")
    print(f"Backend test: {'✅ PASS' if backend_result else '❌ FAIL'}")
    
    if direct_result and router_result and not backend_result:
        print("\nDiagnosis: The issue appears to be in the backend's handling of the move analysis request.")
    elif direct_result and not router_result:
        print("\nDiagnosis: The issue appears to be in the router's handling of the move analysis request.")
    elif not direct_result:
        print("\nDiagnosis: The move analysis microservice itself is rejecting the request.")