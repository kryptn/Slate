FROM python:3.6-alpine3.7

RUN mkdir /app
WORKDIR /app

ADD ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

ADD . /app
RUN python setup.py install

EXPOSE 8080:8080

CMD python slate runserver