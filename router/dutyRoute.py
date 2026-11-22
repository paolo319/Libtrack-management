"""Duty kiosk API: today's board and one-tap card scans.

The monitor's identity comes only from the server session. Duty lookups are
scoped to that monitor's school, and card UIDs are never returned.
"""

from collections import deque
from datetime import date, datetime, timedelta, timezone
from time import monotonic
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from config import settings
from database import get_db
from models import Duty, DutyRecord, Monitor
from schemas import (
    DutyEvent,
    DutyPerson,
    DutyRecordRead,
    DutyScan,
    DutyScanResult,
    DutyToday,
)

router = APIRouter(prefix="/api/duty", tags=["duty"])

TIME_OUT_COOLDOWN = timedelta(hours=1)
MIN_UID_LENGTH, MAX_UID_LENGTH = 4, 64
HEX_DIGITS = frozenset("0123456789ABCDEF")
RATE_WINDOW_SECONDS = 60
_recent_scans: dict[int, deque[float]] = {}


def _today() -> date:
    return datetime.now().astimezone().date()


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _monitor(request: Request, db: Session) -> Monitor:
    """Resolve the monitor from the session, never from client input."""
    try:
        monitor_id = int(request.session.get("monitor_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Please log in again.")

    monitor = db.get(Monitor, monitor_id)
    if monitor is None:
        raise HTTPException(status_code=401, detail="Please log in again.")
    return monitor


def _require_same_origin(request: Request) -> None:
    """Defense in depth against cross-site form posts."""
    origin = request.headers.get("origin")
    if not origin:
        return
    expected = f"{request.url.scheme}://{request.url.netloc}"
    if urlsplit(origin).geturl().rstrip("/") != expected.rstrip("/"):
        raise HTTPException(status_code=403, detail="Cross-origin request rejected.")


def _rate_limit(monitor: Monitor) -> None:
    limit = settings.duty_rate_limit_per_minute
    if limit <= 0:
        return

    now = monotonic()
    window = _recent_scans.setdefault(monitor.id, deque())
    while window and now - window[0] >= RATE_WINDOW_SECONDS:
        window.popleft()
    if len(window) >= limit:
        retry = max(1, int(RATE_WINDOW_SECONDS - (now - window[0])))
        raise HTTPException(
            status_code=429,
            detail="Too many scans. Try again shortly.",
            headers={"Retry-After": str(retry)},
        )
    window.append(now)


def _normalize_uid(raw: str) -> str | None:
    """Uppercase hex only; ignore whitespace and separators from the reader."""
    uid = "".join(char for char in raw.upper() if char.isalnum())
    if not MIN_UID_LENGTH <= len(uid) <= MAX_UID_LENGTH:
        return None
    if any(char not in HEX_DIGITS for char in uid):
        return None
    return uid


def _duty_by_uid(db: Session, monitor: Monitor, uid: str) -> Duty | None:
    duties = db.query(Duty).filter(Duty.school_id == monitor.school_id).all()
    return next((d for d in duties if _normalize_uid(d.rfid) == uid), None)


def _person(duty: Duty) -> DutyPerson:
    return DutyPerson(
        fullname=duty.fullname,
        course=duty.course,
        year_level=duty.year_level,
        logo_url=duty.logo_url,
    )


def _record_read(record: DutyRecord) -> DutyRecordRead:
    return DutyRecordRead(
        id=record.id,
        person=_person(record.duty),
        time_in=record.time_in,
        time_out=record.time_out,
    )


def _today_records(db: Session, monitor: Monitor) -> list[DutyRecordRead]:
    rows = (
        db.query(DutyRecord)
        .options(joinedload(DutyRecord.duty))
        .join(Duty)
        .filter(
            Duty.school_id == monitor.school_id,
            DutyRecord.duty_date == _today(),
        )
        .order_by(DutyRecord.time_in.desc())
        .all()
    )
    records = [_record_read(row) for row in rows]
    records.sort(key=lambda r: _aware(r.time_out or r.time_in), reverse=True)
    return records


def _events(records: list[DutyRecordRead]) -> list[DutyEvent]:
    events: list[DutyEvent] = []
    for record in records:
        events.append(DutyEvent(kind="time_in", at=record.time_in, person=record.person))
        if record.time_out:
            events.append(
                DutyEvent(kind="time_out", at=record.time_out, person=record.person)
            )
    events.sort(key=lambda event: _aware(event.at), reverse=True)
    return events


def _cooldown_message(remaining: timedelta) -> str:
    minutes = max(1, int(remaining.total_seconds() + 59) // 60)
    return f"You can time out in {minutes} minute{'s' if minutes != 1 else ''}."


def _record_scan(db: Session, monitor: Monitor, uid: str) -> DutyScanResult:
    duty = _duty_by_uid(db, monitor, uid)
    if duty is None:
        return DutyScanResult(status="not_found", message="RFID card not registered.")

    person = _person(duty)
    today = _today()
    now = datetime.now(timezone.utc)
    record = (
        db.query(DutyRecord)
        .filter(DutyRecord.duty_id == duty.id, DutyRecord.duty_date == today)
        .first()
    )

    if record is not None:
        if record.time_out is not None:
            status, message = "already_done", f"{duty.fullname} already timed out today."
        else:
            elapsed = now - _aware(record.time_in)
            if elapsed < TIME_OUT_COOLDOWN:
                status = "cooldown"
                message = _cooldown_message(TIME_OUT_COOLDOWN - elapsed)
            else:
                record.time_out = now
                db.commit()
                db.refresh(record)
                status, message = "time_out", f"{duty.fullname} timed out."

        return DutyScanResult(
            status=status,
            message=message,
            person=person,
            record=_record_read(record),
            records=_today_records(db, monitor),
        )

    record = DutyRecord(duty_id=duty.id, duty_date=today, time_in=now)
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent scan already created today's record.
        db.rollback()
        existing = (
            db.query(DutyRecord)
            .filter(DutyRecord.duty_id == duty.id, DutyRecord.duty_date == today)
            .first()
        )
        return DutyScanResult(
            status="already_done",
            message=f"{duty.fullname} already has a record today.",
            person=person,
            record=_record_read(existing) if existing else None,
            records=_today_records(db, monitor),
        )

    db.refresh(record)
    return DutyScanResult(
        status="time_in",
        message=f"{duty.fullname} timed in.",
        person=person,
        record=_record_read(record),
        records=_today_records(db, monitor),
    )


def _scan_response(db: Session, monitor: Monitor, raw_rfid: str) -> DutyScanResult:
    """Validate a raw UID once, then run the shared scan logic."""
    uid = _normalize_uid(raw_rfid)
    if uid is None:
        return DutyScanResult(status="invalid", message="Invalid RFID card.")
    return _record_scan(db, monitor, uid)


@router.get("/today", response_model=DutyToday)
def get_today(request: Request, response: Response, db: Session = Depends(get_db)):
    monitor = _monitor(request, db)
    records = _today_records(db, monitor)
    response.headers["Cache-Control"] = "no-store"
    return DutyToday(
        date=_today().isoformat(),
        count=len(records),
        records=records,
        events=_events(records),
    )


@router.post("/scan", response_model=DutyScanResult, response_model_exclude_none=True)
def scan(
    request: Request,
    response: Response,
    form: Annotated[DutyScan, Form()],
    db: Session = Depends(get_db),
):
    """One tap: record time-in or time-out for the matching duty member."""
    _require_same_origin(request)
    monitor = _monitor(request, db)
    _rate_limit(monitor)
    result = _scan_response(db, monitor, form.rfid)
    response.headers["Cache-Control"] = "no-store"
    return result


