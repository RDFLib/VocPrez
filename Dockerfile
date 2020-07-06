FROM python:3.7.8-slim-buster

COPY requirements.txt .

RUN pip install -r requirements.txt
RUN pip install gunicorn

COPY vocprez/ /vocprez/
WORKDIR /vocprez
ENV PYTHONPATH /

CMD ["gunicorn", "-w", "5", "-b", "0.0.0.0:8001", "vocprez.app:app"]
