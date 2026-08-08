# ---- Stage 1: build SPA ----
FROM node:22-alpine AS spa
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python runtime ----
FROM python:3.12-slim
WORKDIR /srv

COPY backend/pyproject.toml ./backend/
COPY backend/app ./backend/app
RUN pip install --no-cache-dir ./backend

COPY --from=spa /build/dist ./backend/static

ENV TG_DATA_DIR=/data \
    TG_PORT=8000
VOLUME /data
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://localhost:{os.environ.get(\"TG_PORT\",8000)}/healthz')"

WORKDIR /srv/backend
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${TG_PORT}"]
