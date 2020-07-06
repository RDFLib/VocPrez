FROM python:3.7.8-slim-buster

COPY . .

RUN pip install -r requirements.txt
   
RUN pip install gunicorn

    gunicorn python vocprez/app.py
