FROM python:3.7.8-slim-buster

WORKDIR /usr/app

EXPOSE 5000

COPY requirements.txt .
COPY requirements.deploy.txt .

RUN pip install -U pip
RUN pip install -r requirements.txt
RUN pip install -r requirements.deploy.txt

COPY README.md .
COPY wsgi.py .
COPY ./deploy ./vocprez

CMD ["gunicorn", "-w", "5", "-b", "0.0.0.0:5000", "wsgi:application"]
