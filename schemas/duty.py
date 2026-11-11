from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DutyPerson(BaseModel):
    """Public duty identity exposed to the dashboard. No RFID, ever."""

    fullname: str
    logo_url: str


class DutyRecordRead(BaseModel):
    id: int
    person: DutyPerson
    time_in: datetime
    time_out: datetime | None = None


class DutyToday(BaseModel):
    date: str
    count: int
    records: list[DutyRecordRead]


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
