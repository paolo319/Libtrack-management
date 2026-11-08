from datetime import date, datetime, time, timedelta
from time import monotonic

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from database import get_db
from models import Monitor, Student, Visitor
from ocr import read_id

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


def _student_dict(student: Student) -> dict:
    return {
        "fullname": student.fullname,
        "school_id": student.school_id,
        "course": student.course,
        "year_level": student.year_level,
        "school": student.school.value,
    }


def visitors_today(db: Session, monitor_id: int) -> list[dict]:
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
        {**_student_dict(student), "time_in": visit.time_in.isoformat()}
        for visit, student in rows
    ]


def record_visit(db: Session, monitor: Monitor, identifier: str) -> dict:
    student = (
        db.query(Student)
        .filter(Student.school_id == identifier, Student.school == monitor.school)
        .first()
    )

    if student is None:
        # The ID may exist, but at a different school.
        other = db.query(Student).filter(Student.school_id == identifier).first()
        if other is not None:
            return {
                "status": "wrong_school",
                "id": identifier,
                "school": other.school.value,
                "message": f"This ID belongs to {other.school.value}.",
            }
        return {"status": "not_found", "id": identifier}

    visit = Visitor(student_id=student.id, monitor_id=monitor.id)
    db.add(visit)
    db.commit()
    db.refresh(visit)

    return {
        "status": "ok",
        "student": _student_dict(student),
        "time_in": visit.time_in.isoformat(),
    }


@router.get("/visitors/today")
def get_visitors_today(
    request: Request,
    db: Session = Depends(get_db),
):
    monitor = _monitor(request, db)
    visitors = visitors_today(db, monitor.id)
    return {
        "date": datetime.now().date().isoformat(),
        "count": len(visitors),
        "visitors": visitors,
    }


@router.post("/scan/image")
async def scan_image(
    request: Request,
    image: UploadFile = File(...),
    mode: str = Form("auto"),
    db: Session = Depends(get_db),
):
    monitor = _monitor(request, db)

    data = await image.read()
    identifier = await run_in_threadpool(read_id, data)
    if identifier is None:
        return {"status": "unrecognized", "message": "No student ID found in the image."}

    if mode == "auto":
        key = (monitor.id, identifier)
        now = monotonic()
        if now - _recent.get(key, 0) < DEBOUNCE_SECONDS:
            return {
                "status": "duplicate",
                "id": identifier,
                "message": "Already recorded a moment ago.",
            }
        _recent[key] = now

    result = record_visit(db, monitor, identifier)
    result["visitors"] = visitors_today(db, monitor.id)
    return result


@router.post("/scan/manual")
def scan_manual(
    request: Request,
    id: str = Form(...),
    db: Session = Depends(get_db),
):
    monitor = _monitor(request, db)

    identifier = id.strip()
    if not identifier.replace("-", "").isdigit():
        return {"status": "invalid", "message": "Use the format 00-0000-000000."}

    result = record_visit(db, monitor, identifier)
    result["visitors"] = visitors_today(db, monitor.id)
    return result
