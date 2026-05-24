# SDAI · Sistema de Detección y Alertas de Intrusiones
# Multi-purpose: backend FastAPI + (optional) live sniffer en una sola imagen.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend:/app

# Dependencias OS:
# - libpcap + tcpdump → Scapy sniffer (modo prom y captura raw)
# - gcc/libc6-dev    → compilar wheels nativos (bcrypt, scapy)
# - curl             → healthcheck HTTP
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpcap-dev tcpdump \
      gcc libc6-dev \
      curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) Dependencias Python (cacheable layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Código de aplicación + assets + sniffer + scripts + schemas
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY SDAI/    ./SDAI/
COPY db/      ./db/
COPY scripts/ ./scripts/

# 3) Variables de entorno: opcional inyectar .env vía bind mount en compose.
#    Se respeta lo que provea el host; aquí no se hornea ningún secreto.

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=4s --start-period=10s --retries=3 \
  CMD curl --fail --silent http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
