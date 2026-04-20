from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..anti_spam import exceeds_report_burst, is_duplicate_description
from ..config import settings
from ..crud import create_audit_log, create_report, get_clusters, get_report, list_reports, update_report_status
from ..db import get_db
from ..rate_limit import rate_limit_dependency
from ..schemas import ClusterOut, ReportCreate, ReportOut, ReportStatusUpdate
from ..security import require_roles

router = APIRouter(tags=["reports"])


def get_redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def _serialize_report(db: Session, report) -> ReportOut:
    lat_lng = db.execute(
        text("SELECT ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lng FROM reports WHERE id = :id"),
        {"id": str(report.id)},
    ).mappings().first()

    return ReportOut(
        id=report.id,
        channel=report.channel,
        damage_type=report.damage_type,
        severity=report.severity,
        status=report.status,
        description=report.description,
        latitude=float(lat_lng["lat"]),
        longitude=float(lat_lng["lng"]),
        address=report.address,
        reporter_id=report.reporter_id,
        reporter_name=report.reporter_name,
        photo_count=report.photo_count,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.post(
    "/api/v1/reports",
    response_model=ReportOut,
    status_code=201,
    dependencies=[Depends(rate_limit_dependency)],
)
def create_report_handler(payload: ReportCreate, db: Session = Depends(get_db)):
    if exceeds_report_burst(payload.reporter_id, max_per_hour=10):
        raise HTTPException(status_code=429, detail="Hourly reporting limit exceeded")
    if is_duplicate_description(payload.description, payload.reporter_id):
        raise HTTPException(status_code=409, detail="Potential duplicate report text")

    item = create_report(db, payload)

    redis_client = get_redis()
    redis_client.publish("reports:new", str(item.id))
    redis_client.xadd(
        settings.REDIS_STREAM_REPORTS,
        {
            "event": "report_created",
            "report_id": str(item.id),
            "channel": item.channel,
            "severity": item.severity,
        },
    )

    return _serialize_report(db, item)


@router.get("/api/v1/reports", response_model=list[ReportOut], dependencies=[Depends(rate_limit_dependency)])
def list_reports_handler(
    status: str | None = None,
    severity: str | None = None,
    channel: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    items = list_reports(db=db, status=status, severity=severity, channel=channel, limit=limit, offset=offset)
    return [_serialize_report(db, i) for i in items]


@router.get("/api/v1/reports/{report_id}", response_model=ReportOut, dependencies=[Depends(rate_limit_dependency)])
def get_report_handler(report_id: UUID, db: Session = Depends(get_db)):
    item = get_report(db, report_id)
    if not item:
        raise HTTPException(status_code=404, detail="Report not found")
    return _serialize_report(db, item)


@router.patch(
    "/api/v1/reports/{report_id}/status",
    response_model=ReportOut,
    dependencies=[Depends(rate_limit_dependency)],
)
def patch_report_status(
    report_id: UUID,
    payload: ReportStatusUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_roles("verifier", "admin")),
):
    item = get_report(db, report_id)
    if not item:
        raise HTTPException(status_code=404, detail="Report not found")

    old_status = item.status
    updated = update_report_status(db, item, payload.status)

    create_audit_log(
        db=db,
        actor_username=user["sub"],
        action="report.status.updated",
        target_type="report",
        target_id=str(report_id),
        meta={"from": old_status, "to": payload.status},
    )

    return _serialize_report(db, updated)


@router.get("/api/v1/map/clusters", response_model=list[ClusterOut], dependencies=[Depends(rate_limit_dependency)])
def map_clusters_handler(
    precision: int = Query(default=6, ge=3, le=8),
    db: Session = Depends(get_db),
):
    return get_clusters(db, precision=precision)