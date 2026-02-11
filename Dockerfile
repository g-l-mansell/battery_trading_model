FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update
RUN apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
RUN apt update && apt install -y openssh-client

RUN pip install --no-cache-dir uv

COPY pyproject.toml .
COPY src ./src
RUN uv pip install --system -e . --no-cache-dir

COPY . .
RUN pre-commit install || true

CMD ["python", "-m", "battery_trading_model.main"]
