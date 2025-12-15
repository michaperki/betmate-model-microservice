#!/usr/bin/env bash
set -euo pipefail

IMAGE=wdl
# Resolve paths relative to this script so it works from any cwd
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
DIR="$SCRIPT_DIR/src/lambdas/wdl"

AWS_REGION=${AWS_REGION:-us-east-1}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPO_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE:latest"

echo "Building image '$IMAGE' from context: $DIR"
docker build -t $IMAGE "$DIR"

echo "Logging into ECR: $ACCOUNT_ID in $AWS_REGION"
aws ecr get-login-password --region $AWS_REGION \
| docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

echo "Tagging and pushing to $REPO_URI"
docker tag $IMAGE:latest "$REPO_URI"
docker push "$REPO_URI"
echo "Pushed $REPO_URI"
