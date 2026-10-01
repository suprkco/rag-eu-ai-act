# Single public container: static web client + FastAPI on one origin, BM25 only (no model, no secrets).
FROM node:24-alpine AS web
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web .
ENV STATIC_EXPORT=1 NEXT_PUBLIC_API_URL=same-origin NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home appuser
COPY app app
COPY data data
COPY --from=web /web/out static
ENV STATIC_DIR=/app/static ALLOWED_MODES=extractive WEB_ORIGINS=
USER appuser
EXPOSE 8000
# Render, Railway and Fly inject PORT.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
