from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..crud import get_severity_distribution, get_timeline
from ..db import get_db
from ..schemas import SeverityPoint, TimelinePoint

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/timeline", response_model=list[TimelinePoint])
def timeline_handler(hours: int = Query(default=24, ge=1, le=720), db: Session = Depends(get_db)):
    return get_timeline(db, hours=hours)


@router.get("/severity", response_model=list[SeverityPoint])
def severity_handler(hours: int = Query(default=24, ge=1, le=720), db: Session = Depends(get_db)):
    return get_severity_distribution(db, hours=hours)