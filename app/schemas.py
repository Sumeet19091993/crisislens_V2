from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


Channel = Literal["pwa", "web", "whatsapp", "sms"]
Severity = Literal["critical", "high", "medium", "low"]
Status = Literal["new", "verified", "responding", "resolved"]


class ReportCreate(BaseModel):
    channel: Channel
    damage_type: str = Field(min_length=2, max_length=50)
    severity: Severity = "medium"
    description: str | None = None
    latitude: float
    longitude: float
    address: str | None = None
    reporter_id: str | None = None
    reporter_name: str | None = None


class ReportStatusUpdate(BaseModel):
    status: Status


class ReportOut(BaseModel):
    id: UUID
    channel: Channel
    damage_type: str
    severity: Severity
    status: Status
    description: str | None
    latitude: float
    longitude: float
    address: str | None
    reporter_id: str | None
    reporter_name: str | None
    photo_count: int
    created_at: datetime
    updated_at: datetime | None


class ClusterOut(BaseModel):
    geohash: str
    count: int
    critical: int
    high: int
    medium: int
    low: int
    centroid_lat: float
    centroid_lng: float


class TimelinePoint(BaseModel):
    bucket: str
    total: int
    critical: int
    high: int
    medium: int
    low: int


class SeverityPoint(BaseModel):
    severity: Severity
    total: int