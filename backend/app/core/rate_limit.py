import time
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# Simple in-memory token bucket per IP+path. Defaults: 60 req/min general,
# 10 req/min for sensitive POSTs. Tune via env if needed.
SENSITIVE = ("/v1/chat/completions", "/api/dex/swap", "/api/personas/import",
             "/api/personas/register", "/api/admin/auth/login")
GENERAL_RPM = 120
SENSITIVE_RPM = 20
_buckets = {}

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/ready", "/version"):
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        path = request.url.path
        sensitive = any(path == s or path.startswith(s) for s in SENSITIVE)
        limit = SENSITIVE_RPM if sensitive else GENERAL_RPM
        now = time.time()
        key = (ip, path if sensitive else "general")
        window_start, count = _buckets.get(key, (now, 0))
        if now - window_start > 60:
            window_start, count = now, 0
        count += 1
        _buckets[key] = (window_start, count)
        if count > limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Slow down.")
        return await call_next(request)
