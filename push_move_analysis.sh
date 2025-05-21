#!/usr/bin/env bash
set -euo pipefail

IMAGE=move-analysis
DIR=src/lambdas/move_analysis

AWS_REGION=${AWS_REGION:-us-east-1}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPO_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE:latest"

# Build & push
docker build -t $IMAGE "$DIR"
aws ecr get-login-password --region $AWS_REGION \
| docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
docker tag $IMAGE:latest "$REPO_URI"
docker push "$REPO_URI"
echo "Pushed $REPO_URI"