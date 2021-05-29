#!/bin/bash
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 772653926123.dkr.ecr.us-west-2.amazonaws.com
docker build -t top-moves-image ./src/lambdas/top_moves/
docker tag top-moves-image:latest 772653926123.dkr.ecr.us-west-2.amazonaws.com/top-moves-image:latest
docker push 772653926123.dkr.ecr.us-west-2.amazonaws.com/top-moves-image:latest