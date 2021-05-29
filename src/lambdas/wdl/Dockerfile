FROM amazon/aws-lambda-python

COPY . .

RUN pip install -r requirements.txt

CMD [ "wdl.wdl_route" ]