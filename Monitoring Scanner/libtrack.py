from typing import Annotated

from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from config import settings
from database import Base, engine, get_db
from models import Monitor, School
from router.dutyRoute import router as duty_router
from router.scannerRoute import router as scanner_router
from schemas import MonitorLogin
 #python.exe -m uvicorn --app-dir "Monitoring Scanner" libtrack:app --reload
app = FastAPI()
app.add_middleware(
    SessionMiddleware, secret_key=settings.secret_key, same_site="strict"
)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(scanner_router)
app.include_router(duty_router)
templates = Jinja2Templates(directory="Templates")

# Creates missing tables. Existing data is left untouched.
Base.metadata.create_all(bind=engine)


def find_school(db: Session, text: str) -> School | None:
    text = text.strip().lower()
    return (
        db.query(School)
        .filter(
            (func.lower(School.code) == text) | (func.lower(School.name) == text)
        )
        .first()
    )


def login_context(db: Session, error: str | None = None) -> dict:
    schools = (
        db.query(School)
        .filter(School.is_active.is_(True))
        .order_by(School.name)
        .all()
    )
    return {"schools": schools, "error": error}


@app.get("/")
def landing_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/login")
def login_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="monitorLogin.html",
        context=login_context(db),
    )


@app.post("/login")
def login(
    request: Request,
    form: Annotated[MonitorLogin, Form()],
    db: Session = Depends(get_db),
):
    school = find_school(db, form.school)
    monitor = None
    if school is not None:
        monitor = (
            db.query(Monitor)
            .filter(Monitor.area == form.area, Monitor.school_id == school.id)
            .first()
        )

    if monitor and monitor.password == form.password:
        request.session["monitor_id"] = monitor.id
        request.session["area"] = monitor.area
        request.session["school"] = monitor.school.name
        request.session["school_logo"] = monitor.school.logo_url
        return RedirectResponse(url="/monitor", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="monitorLogin.html",
        context=login_context(db, "Invalid area, institution, or password."),
    )


@app.get("/monitor")
def monitor_page(request: Request):
    if request.session.get("monitor_id") is None:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="monitorDashboard.html",
        context={
            "area": request.session.get("area"),
            "school": request.session.get("school"),
            "school_logo": request.session.get("school_logo"),
        },
    )


@app.get("/dutyDashboard")
def duty_page(request: Request):
    if request.session.get("monitor_id") is None:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="monitorDuty.html",
        context={
            "area": request.session.get("area"),
            "school": request.session.get("school"),
            "school_logo": request.session.get("school_logo"),
        },
    )