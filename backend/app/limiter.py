"""Rate limiting per IP address (slowapi), against password guessing and spam.

Behind a reverse proxy in production, the proxy must pass the real client IP.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
