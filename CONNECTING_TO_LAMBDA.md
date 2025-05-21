# Connecting to AWS Lambda Microservice

This guide explains how to connect the Betmate backend to the AWS Lambda microservices for chess analysis.

## API Endpoints

The microservice provides three main endpoints through API Gateway:

1. **WDL (Win/Draw/Loss)** - Calculate probabilities for game outcomes
2. **Top Moves** - Get the best moves for a given position
3. **Move Analysis** - Analyze a specific move on a given board position

### Base URL

The base URL for all endpoints is:
```
https://1g6ow25xjb.execute-api.us-east-1.amazonaws.com/
```

## Authentication

Currently, the API endpoints don't require authentication. In a production environment, you should consider adding API keys or other authentication methods.

## Endpoint Details

### 1. WDL (Win/Draw/Loss)

**Endpoint**: `/wdl`
**Method**: GET

**Query Parameters**:
- `fen` (required): Chess position in FEN notation
- `white_time` (optional): White player's remaining time in seconds (defaults to 60)
- `black_time` (optional): Black player's remaining time in seconds (defaults to 60)

**Example Request**:
```
GET https://1g6ow25xjb.execute-api.us-east-1.amazonaws.com/wdl?fen=rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR%20w%20KQkq%20-%200%201&white_time=60&black_time=60
```

**Example Response**:
```json
{
  "message": "SUCCESS",
  "data": {
    "white_win": 0.42,
    "draw": 0.12,
    "black_win": 0.46
  }
}
```

### 2. Top Moves

**Endpoint**: `/top-moves`
**Method**: GET

**Query Parameters**:
- `fen` (required): Chess position in FEN notation
- `n` (required): Number of top moves to return

**Example Request**:
```
GET https://1g6ow25xjb.execute-api.us-east-1.amazonaws.com/top-moves?fen=rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR%20w%20KQkq%20-%200%201&n=3
```

**Example Response**:
```json
{
  "message": "SUCCESS",
  "data": ["f3", "Nf3", "c4"]
}
```

### 3. Move Analysis

**Endpoint**: `/move-analysis`
**Method**: GET

**Query Parameters**:
- `fen` (required): Chess position in FEN notation
- `move` (required): Move to analyze in SAN notation (e.g., "e4", "Nf3")

**Example Request**:
```
GET https://1g6ow25xjb.execute-api.us-east-1.amazonaws.com/move-analysis?fen=rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR%20w%20KQkq%20-%200%201&move=e4
```

**Example Response**:
```json
{
  "message": "SUCCESS",
  "data": {
    "score": 11,
    "percentile": 79,
    "is_best_move": false
  }
}
```

## Error Handling

All endpoints return errors in a consistent format:

```json
{
  "error": "Error type",
  "message": "Detailed error message"
}
```

Common error types:
- `Argument error`: Invalid or missing parameters
- `Invalid move`: Move is not valid for the given position (includes list of valid moves)

## CORS Configuration

**IMPORTANT**: Currently, the API Gateway is not configured for CORS, which means browser requests from the frontend will be blocked. To enable CORS, you need to:

1. Go to the AWS API Gateway console
2. Select the API (1g6ow25xjb)
3. For each resource (wdl, top-moves, move-analysis):
   - Select the resource
   - Click on "Actions" > "Enable CORS"
   - Enable the following headers:
     - Access-Control-Allow-Origin: '*' (or your specific origin)
     - Access-Control-Allow-Headers: 'Content-Type,X-Amz-Date,Authorization,X-Api-Key'
     - Access-Control-Allow-Methods: 'GET,OPTIONS'
   - Click "Save"
4. Deploy the API to apply the changes

## Integration in the Backend

Here's an example of how to integrate with these endpoints in your Node.js backend:

```javascript
const fetch = require('node-fetch');

// Base URL for API Gateway
const API_BASE_URL = 'https://1g6ow25xjb.execute-api.us-east-1.amazonaws.com';

// Get win/draw/loss probabilities
async function getWdlProbabilities(fen, whiteTime = 60, blackTime = 60) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/wdl?fen=${encodeURIComponent(fen)}&white_time=${whiteTime}&black_time=${blackTime}`
    );
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Failed to get WDL probabilities');
    }
    
    const data = await response.json();
    return data.data;
  } catch (error) {
    console.error('Error fetching WDL probabilities:', error);
    throw error;
  }
}

// Get top moves
async function getTopMoves(fen, n = 3) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/top-moves?fen=${encodeURIComponent(fen)}&n=${n}`
    );
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Failed to get top moves');
    }
    
    const data = await response.json();
    return data.data;
  } catch (error) {
    console.error('Error fetching top moves:', error);
    throw error;
  }
}

// Analyze a specific move
async function analyzeMoveQuality(fen, move) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/move-analysis?fen=${encodeURIComponent(fen)}&move=${move}`
    );
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Failed to analyze move');
    }
    
    const data = await response.json();
    return data.data;
  } catch (error) {
    console.error('Error analyzing move:', error);
    throw error;
  }
}

module.exports = {
  getWdlProbabilities,
  getTopMoves,
  analyzeMoveQuality
};
```

## Rate Limiting and Performance Considerations

- Each Lambda function has computation limits and may time out for complex positions
- Consider implementing caching for frequently requested positions
- API Gateway has built-in throttling, but you may want to implement additional rate limiting in your backend
- For high-traffic applications, consider implementing a queue system for analysis requests

## Troubleshooting

1. **Internal Server Error**: This usually means there was an error in the Lambda function. Check CloudWatch logs for details.
2. **CORS Errors**: If you see errors about Cross-Origin Resource Sharing in the browser console, make sure CORS is configured correctly in API Gateway.
3. **Timeout Errors**: For complex positions, the Lambda function might time out. Try increasing the timeout in the Lambda configuration.
4. **Invalid FEN**: Make sure the FEN string is properly URL-encoded and represents a valid chess position.

## Monitoring and Logging

All Lambda invocations are logged to CloudWatch. For troubleshooting, check the CloudWatch logs in the AWS console.