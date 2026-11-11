from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StudentRead(BaseModel):
    """Student information embedded in scan results and visitor lists."""

    fullname: str
    school_id: str
    course: str
    year_level: str
    school: str


class VisitorRead(StudentRead):
    """A recorded visit, including when the student entered."""

    time_in: datetime


class VisitorsToday(BaseModel):
    """Response for GET /api/visitors/today."""

    date: str
    count: int
    visitors: list[VisitorRead]


ScanStatus = Literal[
    "ok",
    "wrong_school",
    "not_found",
    "unrecognized",
    "duplicate",
    "invalid",
]


class ScanResult(BaseModel):
    """Response shared by the image and manual scan endpoints."""

    status: ScanStatus
    id: str | None = None
    school: str | None = None
    message: str | None = None
    student: StudentRead | None = None
    time_in: datetime | None = None
    visitors: list[VisitorRead] | None = None


class ImageScan(BaseModel):
    """Multipart form fields sent with POST /api/scan/image."""

    mode: Literal["auto", "manual"] = "auto"


class ManualScan(BaseModel):
    """Multipart form fields sent with POST /api/scan/manual."""

    model_config = ConfigDict(populate_by_name=True)

    identifier: str = Field(validation_alias="id")
