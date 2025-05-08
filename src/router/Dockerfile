FROM python:3.8.10-buster

COPY . .

RUN apt-get update && apt-get install -y python3-distutils
RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["python", "router.py"]
