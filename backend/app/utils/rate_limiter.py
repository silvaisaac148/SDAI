"""In-memory sliding window rate limiter for public and sensitive endpoints.

Thread-safe, zero-dependency, and proxy-aware to support production environments
running behind reverse proxies like Nginx, Traefik, or Cloudflare.
"""
import time
from collections import defaultdict
from threading import Lock
from fastapi import Request, HTTPException, status


class RateLimiter:
    def __init__(self, limit: int = 300, window_seconds: int = 60, detail_message: str = "Límite de tasa excedido."):
        self.limit = limit
        self.window_seconds = window_seconds
        self.detail_message = detail_message
        self.history = defaultdict(list)
        self.lock = Lock()

    def __call__(self, request: Request):
        # 1. Resolve proxy IP headers hierarchically to get the true client IP
        ip = "127.0.0.1"
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            # X-Forwarded-For can contain multiple IPs, the first one is the client
            ip = xff.split(",")[0].strip()
        else:
            xri = request.headers.get("X-Real-IP")
            if xri:
                ip = xri.strip()
            elif request.client:
                ip = request.client.host

        now = time.time()
        with self.lock:
            # Keep only timestamps that fall within the current sliding window
            self.history[ip] = [t for t in self.history[ip] if now - t < self.window_seconds]
            
            if len(self.history[ip]) >= self.limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=self.detail_message
                )
            
            # Record current request timestamp
            self.history[ip].append(now)


# Global rate limiter instance specifically for events ingestion protection (300 req/min)
ingest_rate_limiter = RateLimiter(
    limit=300, 
    window_seconds=60, 
    detail_message="Demasiadas peticiones. Límite de tasa de ingestión excedido en el endpoint público."
)

# Global rate limiter instance for security authentication protection (5 req/min)
login_rate_limiter = RateLimiter(
    limit=5, 
    window_seconds=60, 
    detail_message="Demasiados intentos de inicio de sesión. Por favor, espera 60 segundos antes de volver a intentar."
)
