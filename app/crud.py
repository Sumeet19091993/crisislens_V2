import json

from sqlalchemy import desc, select, text
from sqlalchemy.orm import Session

from .models import AuditLog, Report
from .schemas import ReportCreate


def create_report(db: Session, payload: ReportCreate) -> Report:
    item = Report(
        channel=payload.channel,
        damage_type=payload.damage_type,
        severity=payload.severity,
        status="new",
        description=payload.description,
        location=text(f"ST_SetSRID(ST_MakePoint({payload.longitude}, {payload.latitude}), 4326)::geography"),
        address=payload.address,
        reporter_id=payload.reporter_id,
        reporter_name=payload.reporter_name,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_reports(
    db: Session,
    status: str | None = None,
    severity: str | None = None,
    channel: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    stmt = select(Report)

    if status:
        stmt = stmt.where(Report.status == status)
    if severity:
        stmt = stmt.where(Report.severity == severity)
    if channel:
        stmt = stmt.where(Report.channel == channel)

    stmt = stmt.order_by(desc(Report.created_at)).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def get_report(db: Session, report_id):
    stmt = select(Report).where(Report.id == report_id)
    return db.scalar(stmt)


def update_report_status(db: Session, report: Report, status: str) -> Report:
    report.status = status
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_clusters(db: Session, precision: int = 6):
    sql = text(
        """
        SELECT
            ST_GeoHash(location::geometry, :precision) AS geohash,
            COUNT(*)::int AS count,
            SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END)::int AS critical,
            SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END)::int AS high,
            SUM(CASE WHEN severity = 'medium' THEN 1 ELSE 0 END)::int AS medium,
            SUM(CASE WHEN severity = 'low' THEN 1 ELSE 0 END)::int AS low,
            AVG(ST_Y(location::geometry))::float AS centroid_lat,
            AVG(ST_X(location::geometry))::float AS centroid_lng
        FROM reports
        GROUP BY geohash
        ORDER BY count DESC
        """
    )
    rows = db.execute(sql, {"precision": precision}).mappings().all()
    return [dict(r) for r in rows]


def get_timeline(db: Session, hours: int = 24):
    sql = text(
        """
        SELECT
            to_char(date_trunc('hour', created_at), 'YYYY-MM-DD"T"HH24:00:00"Z"') AS bucket,
            COUNT(*)::int AS total,
            SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END)::int AS critical,
            SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END)::int AS high,
            SUM(CASE WHEN severity = 'medium' THEN 1 ELSE 0 END)::int AS medium,
            SUM(CASE WHEN severity = 'low' THEN 1 ELSE 0 END)::int AS low
        FROM reports
        WHERE created_at >= NOW() - (:hours || ' hours')::interval
        GROUP BY date_trunc('hour', created_at)
        ORDER BY date_trunc('hour', created_at)
        """
    )
    rows = db.execute(sql, {"hours": hours}).mappings().all()
    return [dict(r) for r in rows]


def get_severity_distribution(db: Session, hours: int = 24):
    sql = text(
        """
        SELECT severity, COUNT(*)::int AS total
        FROM reports
        WHERE created_at >= NOW() - (:hours || ' hours')::interval
        GROUP BY severity
        ORDER BY total DESC
        """
    )
    rows = db.execute(sql, {"hours": hours}).mappings().all()
    return [dict(r) for r in rows]


def create_audit_log(
    db: Session,
    actor_username: str,
    action: str,
    target_type: str,
    target_id: str,
    meta: dict | None = None,
):
    row = AuditLog(
        actor_username=actor_username,
        action=action,
        target_type=target_type,
        target_id=target_id,
        meta_json=json.dumps(meta or {}),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row