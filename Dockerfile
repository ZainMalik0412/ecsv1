# syntax=docker/dockerfile:1

# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY app/frontend/package.json app/frontend/package-lock.json* ./
RUN npm ci --prefer-offline 2>/dev/null || npm install
COPY app/frontend/ ./
RUN npm run build

# Stage 2: Build Python wheels
FROM python:3.10-slim-bookworm AS backend-builder
WORKDIR /backend
RUN for i in 1 2 3; do \
      apt-get clean && \
      rm -rf /var/lib/apt/lists/* && \
      apt-get update && \
      apt-get install -y --no-install-recommends gcc libpq-dev && \
      break || sleep 5; \
    done && rm -rf /var/lib/apt/lists/*
COPY app/backend/requirements.txt ./
RUN pip install --upgrade pip \
  && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage 3: Runtime
FROM python:3.10-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

RUN for i in 1 2 3; do \
      apt-get clean && \
      rm -rf /var/lib/apt/lists/* && \
      apt-get update && \
      apt-get install -y --no-install-recommends libpq5 curl && \
      break || sleep 5; \
    done && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 10001 appuser

COPY --from=backend-builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY app/backend/ /app/backend/
COPY --from=frontend-builder /frontend/dist /app/backend/app/static/

WORKDIR /app/backend
USER appuser
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
