"""
JODOHKU.MY — Rate Limiter Middleware
Prevents abuse and brute-force attacks
"""

from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import Request, HTTPException


# In-memory rate limiter (use Redis in production)
_rate_store: dict = defaultdict(list)


async def rate_limit(request: Request, limit: int = 60, window_seconds: int = 60):
    """
    Simple rate limiter.
    Production: Replace with Redis-based sliding window.
    """
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{request.url.path}"
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=window_seconds)
    
    # Clean old entries
    _rate_store[key] = [t for t in _rate_store[key] if t > cutoff]
    
    if len(_rate_store[key]) >= limit:
        raise HTTPException(
            status_code=429,
            detail="Terlalu banyak permintaan. Sila cuba sebentar lagi."
        )
    
    _rate_store[key].append(now)
