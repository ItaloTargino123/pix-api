FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ .
COPY build.sh .
RUN chmod +x build.sh

EXPOSE 8000

# Em produção, sem --reload
CMD ["sh", "-c", "./build.sh && uvicorn config.asgi:application --host 0.0.0.0 --port ${PORT:-8000}"]
