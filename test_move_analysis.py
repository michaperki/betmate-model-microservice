import requests
import json

# Test a simple move analysis request
test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
test_move = "e4"

print(f"Testing move analysis for FEN: {test_fen}")
print(f"Move to analyze: {test_move}")

try:
    # Direct request to the move-analysis microservice - NOTE: Port is 8083 based on docker ps output
    response = requests.post(
        "http://localhost:8083/predict",  # Fixed port to match the correct container
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
        result = response.json()
        print("Response:")
        print(json.dumps(result, indent=2))
        
        # Extract and validate the data
        if "body" in result:
            try:
                body = json.loads(result["body"])
                print("\nBody content:")
                print(json.dumps(body, indent=2))
                
                if "data" in body:
                    data = body["data"]
                    print("\nAnalysis data:")
                    print(json.dumps(data, indent=2))
                    
                    # Check if the data contains the required fields
                    if "move" in data and "percentile" in data and "is_best_move" in data:
                        print("\n✅ VALID RESPONSE: Contains all required fields")
                    else:
                        print("\n❌ INVALID RESPONSE: Missing required fields")
                        missing = []
                        if "move" not in data:
                            missing.append("move")
                        if "percentile" not in data:
                            missing.append("percentile")
                        if "is_best_move" not in data:
                            missing.append("is_best_move")
                        print(f"Missing fields: {', '.join(missing)}")
                else:
                    print("\n❌ INVALID RESPONSE: No data field in the body")
            except json.JSONDecodeError:
                print("\n❌ INVALID RESPONSE: Body is not valid JSON")
                print(f"Raw body: {result['body']}")
        else:
            print("\n❌ INVALID RESPONSE: No body field in response")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Error making request: {e}")