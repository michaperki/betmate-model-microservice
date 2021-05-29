FROM python:3.8.10-alpine3.12

COPY . .

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["python", "router.py"]