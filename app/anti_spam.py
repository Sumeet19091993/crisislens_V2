import hashlib
import time
from redis import Redis

from .config import settings

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def is_duplicate_description(description: str | None, reporter_id: str | None) -> bool:
    if not description or not reporter_id:
        return False

    normalized = " ".join(description.lower().split())
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    key = f"dup:{reporter_id}:{digest}"

    if redis_client.exists(key):
        return True

    redis_client.setex(key, 21600, "1")  # 6 hours
    return False


def exceeds_report_burst(reporter_id: str | None, max_per_hour: int = 10) -> bool:
    if not reporter_id:
        return False

    hour_bucket = int(time.time() // 3600)
    key = f"burst:{reporter_id}:{hour_bucket}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, 3900)
    return count > max_per_hour