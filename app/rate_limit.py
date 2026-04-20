import time
from fastapi import Request, HTTPException
from redis import Redis

from .config import settings

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def _client_key(request: Request) -> str:
    device = request.headers.get("x-device-id")
    if device:
        return f"device:{device}"
    ip = request.client.host if request.client else "unknown"
    return f"ip:{ip}"


async def rate_limit_dependency(request: Request):
    key = _client_key(request)
    minute_bucket = int(time.time() // 60)
    redis_key = f"rl:{key}:{minute_bucket}"

    count = redis_client.incr(redis_key)
    if count == 1:
        redis_client.expire(redis_key, 90)

    if count > 120:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")