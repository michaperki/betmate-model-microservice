
FROM public.ecr.aws/lambda/python:3.8
RUN yum update -y && yum install -y unzip

WORKDIR /var/task
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target .

# Copy Python code
COPY wdl.py .
COPY logger.py .

# Copy assets
COPY assets/stockfish_linux assets/stockfish_linux
COPY assets/black_win_fraction.npy assets/black_win_fraction.npy
COPY assets/white_win_fraction.npy assets/white_win_fraction.npy
COPY assets/draw_fraction.npy assets/draw_fraction.npy

# Ensure binary is executable
RUN chmod +x assets/stockfish_linux

# Set environment variable for Stockfish path
ENV STOCKFISH_PATH=/var/task/assets/stockfish_linux

CMD ["wdl.handler"]
