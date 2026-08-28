# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

# Predictable Python behaviour in containers: no .pyc files, unbuffered logs
# so `docker compose logs` streams in real time.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies are copied and installed on their own layer so that source
# changes do not invalidate the (slow) pip install.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non-root user.
RUN useradd --create-home --uid 1000 aegis \
    && chown -R aegis:aegis /app
USER aegis

EXPOSE 8000

# --reload is supplied by docker-compose for development; the image default is
# a plain production-style run.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
