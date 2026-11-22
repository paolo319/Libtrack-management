from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DutyPerson(BaseModel):
    """Duty member shown on the board."""

    fullname: str
    course: str
    year_level: str
    logo_url: str


class DutyRecordRead(BaseModel):
    """One duty record with the member and their times."""

    id: int
    person: DutyPerson
    time_in: datetime
    time_out: datetime | None = None


class DutyEvent(BaseModel):
    """A time-in or time-out event."""

    kind: Literal["time_in", "time_out"]
    at: datetime
    person: DutyPerson


class DutyToday(BaseModel):
    """Response for GET /api/duty/today."""

    date: str
    count: int
    records: list[DutyRecordRead]
    events: list[DutyEvent]


class DutyScan(BaseModel):
    """Raw card UID typed by the reader."""

    rfid: str


class DutyScanResult(BaseModel):
    """Response for POST /api/duty/scan."""

    status: Literal[
        "time_in", "time_out", "cooldown", "already_done", "not_found", "invalid"
    ]
    message: str
    person: DutyPerson | None = None
    record: DutyRecordRead | None = None
    records: list[DutyRecordRead] | None = None
