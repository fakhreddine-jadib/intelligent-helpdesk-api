"""Request rate limiting.
Storage is Redis when REDIS_URL is set, in-memory otherwise. Redis
matters in production: limits then persist across restarts and are
shared between application processes."""
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=os.environ.get("REDIS_URL", "memory://"),
)