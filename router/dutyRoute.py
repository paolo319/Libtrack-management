import secrets
from collections import deque
from datetime import date, datetime, timedelta, timezone
from time import monotonic
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import Duty, DutyRecord, Monitor
from schemas import DutyPerson, DutyRecordRead, DutyScan, DutyScanResult, DutyToday

router = APIRouter(prefix="/api/duty", tags=["duty"])

# A duty member must stay at least this long before they can time out.
TIME_OUT_COOLDOWN = timedelta(hours=1)
MIN_RFID_LENGTH = 4
MAX_RFID_LENGTH = 64
HEX_DIGITS = set("0123456789ABCDEF")
RATE_WINDOW_SECONDS = 60
_recent_scans: dict[int, deque[float]] = {}


def _today() -> date:
    return datetime.now().astimezone().date()


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _monitor(request: Request, db: Session) -> Monitor:
    monitor_id = request.session.get("monitor_id")
    if monitor_id is None:
        raise HTTPException(status_code=401, detail="Please log in again.")

    monitor = db.get(Monitor, int(monitor_id))
    if monitor is None:
        raise HTTPException(status_code=401, detail="Please log in again.")

    return monitor


def _device_monitor(request: Request, db: Session) -> Monitor:
    """Authenticate the RFID bridge with its scoped device token."""
    token = settings.duty_bridge_token
    monitor_id = settings.duty_monitor_id
    if not token or monitor_id is None:
        raise HTTPException(status_code=401, detail="Duty bridge is not configured.")

    provided = request.headers.get("x-duty-token", "")
    if not secrets.compare_digest(provided, token):
        raise HTTPException(status_code=401, detail="Invalid device token.")

    monitor = db.get(Monitor, monitor_id)
    if monitor is None:
        raise HTTPException(status_code=401, detail="Duty bridge monitor not found.")

    return monitor


def _check_rate_limit(monitor: Monitor) -> None:
    """Sliding-window limit for scans coming from the device token."""
    limit = settings.duty_rate_limit_per_minute
    if limit <= 0:
        return

    now = monotonic()
    window = _recent_scans.setdefault(monitor.id, deque())
    while window and now - window[0] >= RATE_WINDOW_SECONDS:
        window.popleft()

    if len(window) >= limit:
        retry_after = max(1, int(RATE_WINDOW_SECONDS - (now - window[0])))
        raise HTTPException(
            status_code=429,
            detail="Too many scans. Try again shortly.",
            headers={"Retry-After": str(retry_after)},
        )
    window.append(now)


def _normalize_rfid(raw: str) -> str | None:
    """Uppercase hex only. Returns None when the value is not a valid UID."""
    value = "".join(ch for ch in raw.upper() if ch.isalnum())
    if not (MIN_RFID_LENGTH <= len(value) <= MAX_RFID_LENGTH):
        return None
    if any(ch not in HEX_DIGITS for ch in value):
        return None
    return value


def _find_duty(db: Session, monitor: Monitor, uid: str) -> Duty | None:
    duties = db.query(Duty).filter(Duty.school_id == monitor.school_id).all()
    for duty in duties:
        if _normalize_rfid(duty.rfid) == uid:
            return duty
    return None


def _person(duty: Duty) -> DutyPerson:
    return DutyPerson(fullname=duty.fullname, logo_url=duty.logo_url)


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
        .join(Duty)
        .filter(
            Duty.school_id == monitor.school_id,
            DutyRecord.duty_date == _today(),
        )
        .order_by(DutyRecord.time_in.desc())
        .all()
    )
    return [_record_read(record) for record in rows]


def _cooldown_message(remaining: timedelta) -> str:
    total_seconds = max(0, int(remaining.total_seconds()))
    minutes = total_seconds // 60
    if total_seconds % 60:
        minutes += 1
    minutes = max(1, minutes)
    return f"You can time out in {minutes} minute{'s' if minutes != 1 else ''}."


def _scan(db: Session, monitor: Monitor, raw_rfid: str) -> DutyScanResult:
    uid = _normalize_rfid(raw_rfid)
    if uid is None:
        return DutyScanResult(status="invalid", message="Invalid RFID card.")

    duty = _find_duty(db, monitor, uid)
    if duty is None:
        return DutyScanResult(status="not_found", message="RFID card not registered.")

    person = _person(duty)
    today = _today()
    record = (
        db.query(DutyRecord)
        .filter(DutyRecord.duty_id == duty.id, DutyRecord.duty_date == today)
        .first()
    )
    now = datetime.now(timezone.utc)

    if record is not None:
        if record.time_out is not None:
            return DutyScanResult(
                status="already_done",
                message=f"{duty.fullname} already timed out today.",
                person=person,
                record=_record_read(record),
                records=_today_records(db, monitor),
            )

        elapsed = now - _aware(record.time_in)
        if elapsed < TIME_OUT_COOLDOWN:
            return DutyScanResult(
                status="cooldown",
                message=_cooldown_message(TIME_OUT_COOLDOWN - elapsed),
                person=person,
                record=_record_read(record),
                records=_today_records(db, monitor),
            )

        record.time_out = now
        db.commit()
        db.refresh(record)
        return DutyScanResult(
            status="time_out",
            message=f"{duty.fullname} timed out.",
            person=person,
            record=_record_read(record),
            records=_today_records(db, monitor),
        )

    record = DutyRecord(duty_id=duty.id, duty_date=today, time_in=now)
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        # Another request created today's record first; treat it as a duplicate.
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


@router.get("/today", response_model=DutyToday)
def get_today(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    monitor = _monitor(request, db)
    records = _today_records(db, monitor)
    response.headers["Cache-Control"] = "no-store"
    return DutyToday(
        date=_today().isoformat(),
        count=len(records),
        records=records,
    )


@router.post(
    "/scan/device", response_model=DutyScanResult, response_model_exclude_none=True
)
def scan_device(
    request: Request,
    response: Response,
    form: Annotated[DutyScan, Form()],
    db: Session = Depends(get_db),
):
    """The only way to create a duty record: the token-scoped RFID bridge."""
    monitor = _device_monitor(request, db)
    _check_rate_limit(monitor)
    result = _scan(db, monitor, form.rfid)
    response.headers["Cache-Control"] = "no-store"
    return result
