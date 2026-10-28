"""Rate limiting per IP address (slowapi), against password guessing and spam."""

from slowapi import Limiter
from starlette.requests import Request


def client_ip(request: Request) -> str:
    """The patient's IP, also behind the proxy of Render.

    Render's proxy puts the real client IP first in X-Forwarded-For; only that
    first value is used, never the rest of the chain. Without the header (local
    development), the address of the connection.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    first = forwarded.split(",")[0].strip()
    if first:
        return first
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=client_ip)
