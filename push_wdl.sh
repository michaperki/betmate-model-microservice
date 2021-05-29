#!/bin/bash
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 772653926123.dkr.ecr.us-west-2.amazonaws.com
docker build -t wdl-image ./src/wdl/
docker tag wdl-image:latest 772653926123.dkr.ecr.us-west-2.amazonaws.com/wdl-image:latest
docker push 772653926123.dkr.ecr.us-west-2.amazonaws.com/wdl-image:latest