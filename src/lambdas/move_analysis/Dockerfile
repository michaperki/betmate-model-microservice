FROM public.ecr.aws/lambda/python:3.8

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Copy Stockfish engine
COPY assets/stockfish_linux ${LAMBDA_TASK_ROOT}/assets/stockfish_linux
RUN chmod +x ${LAMBDA_TASK_ROOT}/assets/stockfish_linux

# Copy function code
COPY move_analysis.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD [ "move_analysis.move_analysis_route" ]