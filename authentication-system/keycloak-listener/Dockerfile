FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && \
    pip install --no-cache-dir requests pytz psycopg2-binary && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY listener.py .

COPY entrypoint.sh /entrypoint.sh
CMD ["sh", "/entrypoint.sh"]