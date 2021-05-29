FROM amazon/aws-lambda-python

COPY . .

RUN pip install -r requirements.txt

CMD [ "moves.moves_route" ]