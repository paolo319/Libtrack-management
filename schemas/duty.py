from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DutyPerson(BaseModel):
    """Public duty identity exposed to the dashboard. No RFID, ever."""

    fullname: str
    course: str
    year_level: str
    logo_url: str


class DutyRecordRead(BaseModel):
    id: int
    person: DutyPerson
    time_in: datetime
    time_out: datetime | None = None


DutyEventKind = Literal["time_in", "time_out"]


class DutyEvent(BaseModel):
    """A single sign-in or sign-out from today's duty log."""

    kind: DutyEventKind
    at: datetime
    person: DutyPerson


class DutyToday(BaseModel):
    date: str
    count: int
    records: list[DutyRecordRead]
    events: list[DutyEvent]


class DutyScan(BaseModel):
    rfid: str


class DutyScanResult(BaseModel):
    status: Literal[
        "time_in",
        "time_out",
        "cooldown",
        "already_done",
        "not_found",
        "invalid",
    ]
    message: str
    person: DutyPerson | None = None
    record: DutyRecordRead | None = None
    records: list[DutyRecordRead] | None = None
