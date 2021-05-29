FROM amazon/aws-lambda-python

COPY . .

RUN pip install -r requirements.txt

CMD [ "top_moves.top_moves_route" ]