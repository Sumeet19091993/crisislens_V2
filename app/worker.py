import json
import logging
import time

from redis import Redis
from redis.exceptions import ResponseError

from .config import settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("crisislens-worker")


def send_fcm_stub(report_id: str, severity: str):
    log.info("FCM_STUB report_id=%s severity=%s", report_id, severity)


def ensure_group(r: Redis):
    try:
        r.xgroup_create(
            name=settings.REDIS_STREAM_REPORTS,
            groupname=settings.REDIS_STREAM_GROUP,
            id="0",
            mkstream=True,
        )
        log.info("Created stream group")
    except ResponseError as e:
        if "BUSYGROUP" in str(e):
            pass
        else:
            raise


def run():
    r = Redis.from_url(settings.redis_url, decode_responses=True)
    ensure_group(r)
    log.info("Worker started")

    while True:
        items = r.xreadgroup(
            groupname=settings.REDIS_STREAM_GROUP,
            consumername=settings.REDIS_STREAM_CONSUMER,
            streams={settings.REDIS_STREAM_REPORTS: ">"},
            count=20,
            block=5000,
        )

        if not items:
            continue

        for _stream, messages in items:
            for msg_id, payload in messages:
                try:
                    event = payload.get("event")
                    report_id = payload.get("report_id")
                    severity = payload.get("severity", "unknown")

                    log.info("event=%s payload=%s", event, json.dumps(payload))

                    if event == "report_created":
                        send_fcm_stub(report_id, severity)

                    r.xack(settings.REDIS_STREAM_REPORTS, settings.REDIS_STREAM_GROUP, msg_id)
                except Exception:
                    log.exception("Failed processing message %s", msg_id)
                    time.sleep(1)


if __name__ == "__main__":
    run()