import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis import Redis

from ..config import settings

router = APIRouter(tags=["live"])


@router.websocket("/ws/live")
async def live_socket(websocket: WebSocket):
    await websocket.accept()
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis_client.pubsub()
    pubsub.subscribe("reports:new")

    try:
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                payload = {"event": "report_created", "report_id": message["data"]}
                await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    finally:
        pubsub.close()
        redis_client.close()