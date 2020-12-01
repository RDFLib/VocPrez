FROM python:3.7.8-slim-buster

WORKDIR /usr/app

EXPOSE 5000

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY README.md .
ADD ./vocprez ./vocprez

CMD ["gunicorn", "-w", "5", "-b", "0.0.0.0:5000", "vocprez.wsgi:app"]
