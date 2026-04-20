from fastapi import APIRouter, HTTPException
from redis import Redis
from sqlalchemy import text

from ..config import settings
from ..db import engine

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/ready")
def ready():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"db not ready: {e}")

    try:
        r = Redis.from_url(settings.redis_url, decode_responses=True)
        r.ping()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"redis not ready: {e}")

    return {"status": "ready"}