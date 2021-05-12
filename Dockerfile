FROM python:3.9.4-alpine3.13

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY src app
COPY google-credentials.json google-credentials.json

WORKDIR app
ENTRYPOINT ["python", "main.py"]
