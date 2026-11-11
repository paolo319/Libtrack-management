from datetime import date, datetime, time, timedelta
from time import monotonic
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from database import get_db
from models import Monitor, Student, Visitor
from ocr import read_id
from schemas import (
    ImageScan,
    ManualScan,
    ScanResult,
    StudentRead,
    VisitorRead,
    VisitorsToday,
)

router = APIRouter(prefix="/api", tags=["scanner"])

# Auto mode looks at the camera every couple of seconds. Keep the same card from
# being recorded again and again while it is held in front of the lens.
DEBOUNCE_SECONDS = 10
_recent: dict[tuple[int, str], float] = {}


def _monitor(request: Request, db: Session) -> Monitor:
    monitor_id = request.session.get("monitor_id")
    if monitor_id is None:
        raise HTTPException(status_code=401, detail="Please log in again.")

    monitor = db.get(Monitor, int(monitor_id))
    if monitor is None:
        raise HTTPException(status_code=401, detail="Please log in again.")

    return monitor


def _student_read(student: Student) -> StudentRead:
    return StudentRead(
        fullname=student.fullname,
        school_id=student.school_id,
        course=student.course,
        year_level=student.year_level,
        school=student.school.name,
    )


def _visitor_read(visit: Visitor, student: Student) -> VisitorRead:
    return VisitorRead(
        **_student_read(student).model_dump(),
        time_in=visit.time_in,
    )


def visitors_today(db: Session, monitor_id: int) -> list[VisitorRead]:
    """Visits recorded for this monitor during the current local day."""
    start = datetime.combine(date.today(), time.min).astimezone()
    end = start + timedelta(days=1)

    rows = (
        db.query(Visitor, Student)
        .join(Student)
        .filter(
            Visitor.monitor_id == monitor_id,
            Visitor.time_in >= start,
            Visitor.time_in < end,
        )
        .order_by(Visitor.time_in.desc())
        .all()
    )

    return [
        _visitor_read(visit, student)
        for visit, student in rows
    ]


def record_visit(db: Session, monitor: Monitor, identifier: str) -> ScanResult:
    student = (
        db.query(Student)
        .filter(
            Student.school_id == identifier,
            Student.institution_id == monitor.school_id,
        )
        .first()
    )

    if student is None:
        # The ID may exist, but at a different school.
        other = db.query(Student).filter(Student.school_id == identifier).first()
        if other is not None:
            return ScanResult(
                status="wrong_school",
                id=identifier,
                school=other.school.name,
                message=f"This ID belongs to {other.school.name}.",
            )
        return ScanResult(status="not_found", id=identifier)

    visit = Visitor(student_id=student.id, monitor_id=monitor.id)
    db.add(visit)
    db.commit()
    db.refresh(visit)

    return ScanResult(
        status="ok",
        student=_student_read(student),
        time_in=visit.time_in,
    )


@router.get("/visitors/today", response_model=VisitorsToday)
def get_visitors_today(
    request: Request,
    db: Session = Depends(get_db),
):
    monitor = _monitor(request, db)
    visitors = visitors_today(db, monitor.id)
    return VisitorsToday(
        date=datetime.now().date().isoformat(),
        count=len(visitors),
        visitors=visitors,
    )


@router.post("/scan/image", response_model=ScanResult, response_model_exclude_none=True)
async def scan_image(
    request: Request,
    image: UploadFile = File(...),
    form: Annotated[ImageScan, Form()] = ImageScan(),
    db: Session = Depends(get_db),
):
    monitor = _monitor(request, db)

    data = await image.read()
    identifier = await run_in_threadpool(read_id, data)
    if identifier is None:
        return ScanResult(
            status="unrecognized",
            message="No student ID found in the image.",
        )

    if form.mode == "auto":
        key = (monitor.id, identifier)
        now = monotonic()
        if now - _recent.get(key, 0) < DEBOUNCE_SECONDS:
            return ScanResult(
                status="duplicate",
                id=identifier,
                message="Already recorded a moment ago.",
            )
        _recent[key] = now

    result = record_visit(db, monitor, identifier)
    result.visitors = visitors_today(db, monitor.id)
    return result


@router.post("/scan/manual", response_model=ScanResult, response_model_exclude_none=True)
def scan_manual(
    request: Request,
    form: Annotated[ManualScan, Form()],
    db: Session = Depends(get_db),
):
    monitor = _monitor(request, db)

    identifier = form.identifier.strip()
    if not identifier.replace("-", "").isdigit():
        return ScanResult(status="invalid", message="Use the format 00-0000-000000.")

    result = record_visit(db, monitor, identifier)
    result.visitors = visitors_today(db, monitor.id)
    return result
