FROM public.ecr.aws/lambda/python:3.8
RUN yum update -y && yum install -y unzip
WORKDIR /var/task
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target .
COPY move_analysis.py .
COPY assets/stockfish_linux assets/stockfish_linux
RUN chmod +x assets/stockfish_linux
ENV STOCKFISH_PATH=/var/task/assets/stockfish_linux
CMD ["move_analysis.handler"]
