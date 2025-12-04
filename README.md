# Betmate Model Microservice

Collection of computationally intensive functions to analyze chess boards. For use with AWS Lambda.

Link to [main server](https://github.com/dali-lab/betmate-backend)

Link to [frontend client](https://github.com/dali-lab/betmate-frontend)

## Architecture

These functions are written in [Python](https://www.python.org/), and it utilizes the [python-chess](https://python-chess.readthedocs.io/en/latest/) library for chess logic and to interface with the [Stockfish](https://stockfishchess.org/) chess engine. For deployment, each function and its dependencies are packaged in a [Docker](https://www.docker.com/) image to be run in [AWS Lambda](https://aws.amazon.com/lambda/), and each function is triggered through an endpoint from [AWS API Gateway](https://aws.amazon.com/api-gateway/).

## Setup

You must have have `Python 3.7+` installed to develop and test this project, but `Python 3.8` is ideal as that is the runtime used for AWS Lambda.

To run and deploy this project, you must have `Docker` installed and running.

### Base environment
1. Clone the repository
2. `python -m venv ./venv`
3. `source ./venv/bin/activate`
4. `pip3 install -r requirements.txt`

### Testing

The Python module used is `pytest`. Test files are found in `./tests/`.

To run: `pytest`

### Run locally

To emulate the functionality of the AWS API Gateway endpoint and AWS Lambda, Docker Compose is used. It spins up 3 containers. 2 of which are the AWS Lambda functions, `top_moves` and `wdl`, and the other is a "router" that routes requests to the appropriate AWS Lambda container.

To build: `docker-compose build`

To run: `docker compose up`

### Logging noise control

The Python services now default to `LOG_LEVEL=WARNING` to keep local consoles quiet. When you need extra detail, set `LOG_LEVEL` before running Docker (e.g., `LOG_LEVEL=INFO docker compose up` or `$env:LOG_LEVEL="DEBUG"` in PowerShell) and restart the containers.

### Deployment

To put these functions into production, you need to:
1. Download the [AWS CLI](https://aws.amazon.com/cli/)
2. Configure your CLI profile to the **root** user of your AWS account.
3. To deploy `top_moves` and `wdl` run `bash push_top_moves.sh` and `bash push_wdl.sh`, respectively.
4. Navigate in your AWS Console to AWS Lambda, and click on the function of interest.
5. Under the tab "Image", press "Deploy new image".
6. Browse for the image that matches the selected function, and then select the latest image.

## Repository Structure

```
├── README.md
├── assets # models and Stockfish executables
├── src
│   ├── router # request handler for running locally
│   ├── lambdas # all functions, see "Function Structure"
│   └── __init__.py # imports lambdas for testing accessibility
├── tests # testing files
├── lint.sh # linting script
├── push_top_moves.sh # deployment script for top_moves model
├── push_wdl.sh # deployment script for wdl model
├── docker-compose.yml # spec for running locally
└── requirements.txt # python package dependencies
```

## Function Structure

```
├── assets # models and/or Stockfish executables
├── function.py # function source code
├── Dockerfile # spec for AWS Lambda function
└── requirements.txt # python package dependencies
```

## Authors

- Jack Keane '22
- Faustino Cortina '21
- Benedict Tedjokusumo '23
