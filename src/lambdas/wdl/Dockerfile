
FROM public.ecr.aws/lambda/python:3.8
RUN yum update -y && yum install -y unzip

WORKDIR /var/task
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target .

# Copy Python code
COPY wdl.py .
COPY logger.py .

# Copy all assets (tables, engines, nets). Place lc0 and weights.pb(.gz) here to enable LC0.
COPY assets/ assets/

# Ensure binaries are executable when present
RUN chmod +x assets/stockfish_linux || true \
 && chmod +x assets/lc0 || true

# Default engine envs (can be overridden via docker-compose)
ENV STOCKFISH_PATH=/var/task/assets/stockfish_linux

CMD ["wdl.handler"]
