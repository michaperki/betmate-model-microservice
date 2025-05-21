# AWS Lambda Deployment Guide

This document provides instructions for deploying the chess analysis microservices to AWS Lambda.

## Prerequisites

1. AWS CLI installed and configured with appropriate credentials
2. Docker installed and running
3. ECR repositories created for each lambda function:
   - `move-analysis`
   - `top-moves`
   - `wdl`

## Deployment Steps

### 1. Build and Push Docker Images

Each lambda function has its own push script that will:
1. Build the Docker image
2. Authenticate with AWS ECR
3. Tag the image
4. Push the image to ECR

Run the following scripts to deploy each lambda:

```bash
# Deploy move-analysis lambda
./push_move_analysis.sh

# Deploy top-moves lambda
./push_top_moves.sh

# Deploy wdl lambda
./push_wdl.sh
```

### 2. Create Lambda Functions

For each lambda, create a new AWS Lambda function:

1. Go to AWS Lambda console
2. Click "Create function"
3. Select "Container image" as the source
4. Enter a function name (e.g., `move-analysis`, `top-moves`, or `wdl`)
5. Browse for the container image you pushed to ECR
6. Configure basic settings:
   - Memory: 512 MB (minimum recommended)
   - Timeout: 30 seconds
   - Environment variables:
     - `STOCKFISH_PATH`: `/var/task/assets/stockfish_linux`
     - (For development) `LOCAL_DEV`: `false`
   
7. Click "Create function"

### 3. Configure API Gateway

To make the lambdas accessible via HTTP:

1. Go to API Gateway console
2. Create a new REST API
3. Create resources and methods for each endpoint:
   - `GET /move-analysis`
   - `GET /top-moves`
   - `GET /wdl`
4. Configure each method to point to the corresponding Lambda function
5. Enable CORS if needed
6. Deploy the API to a stage (e.g., "dev")

### 4. Testing the Endpoints

Here are sample CURL commands to test each endpoint:

#### Move Analysis

```bash
curl "https://your-api-id.execute-api.us-east-1.amazonaws.com/dev/move-analysis?fen=rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR%20w%20KQkq%20-%200%201&move=e4"
```

Expected response:

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

#### Top Moves

```bash
curl "https://your-api-id.execute-api.us-east-1.amazonaws.com/dev/top-moves?fen=rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR%20w%20KQkq%20-%200%201&n=3"
```

Expected response:

```json
{
  "message": "SUCCESS",
  "data": ["e4", "d4", "Nf3"]
}
```

#### WDL (Win/Draw/Loss)

```bash
curl "https://your-api-id.execute-api.us-east-1.amazonaws.com/dev/wdl?fen=rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR%20w%20KQkq%20-%200%201&white_time=60&black_time=60"
```

Expected response:

```json
{
  "message": "SUCCESS",
  "data": {
    "white_win": 0.38,
    "draw": 0.34,
    "black_win": 0.28
  }
}
```

## Troubleshooting

1. CloudWatch Logs: All logs from the lambdas are sent to CloudWatch. Check these logs for any errors.
2. Cold Start: The first invocation of each lambda might take longer due to cold start time.
3. Memory Issues: If you see out-of-memory errors, increase the memory allocation for the lambda.
4. Timeout Issues: If your lambda times out, increase the timeout setting.

## Maintenance

To update a lambda:

1. Make changes to the source code
2. Run the corresponding push script to build and push a new container image
3. Update the lambda function to use the new image version in the AWS console