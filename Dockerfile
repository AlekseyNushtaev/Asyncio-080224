FROM python:3.10.13-alpine3.18
COPY . /app

WORKDIR /app
COPY requirements.txt /app
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

CMD python main.py