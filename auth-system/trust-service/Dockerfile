FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps necessari per psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    python3-dev \
 && rm -rf /var/lib/apt/lists/*

# copy e install pip deps
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

#EXPOSE 5000 #La porta 5000 è stata omessa sia qui che nel compose in modo che sia raggiungibile solo da OPA-Envoy
CMD ["python", "app.py"]
