from typing import Annotated

from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from config import settings
from database import Base, engine, get_db
from models import Monitor, School
from router.scannerRoute import router as scanner_router

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(scanner_router)
templates = Jinja2Templates(directory="Templates")

# Creates missing tables. Existing data is left untouched.
Base.metadata.create_all(bind=engine)


def find_school(text: str) -> School | None:
    text = text.strip().lower()
    for school in School:
        if text in (school.name.lower(), school.value.lower()):
            return school
    return None


def login_context(error: str | None = None) -> dict:
    return {
        "schools": [{"name": school.name, "label": school.value} for school in School],
        "error": error,
    }


@app.get("/")
def landing_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="monitorLogin.html",
        context=login_context(),
    )


@app.post("/login")
def login(
    request: Request,
    userArea: Annotated[str, Form()],
    userSchool: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: Session = Depends(get_db),
):
    school = find_school(userSchool)
    monitor = None
    if school is not None:
        monitor = (
            db.query(Monitor)
            .filter(Monitor.area == userArea, Monitor.school == school)
            .first()
        )

    if monitor and monitor.password == password:
        request.session["monitor_id"] = monitor.id
        request.session["area"] = monitor.area
        request.session["school"] = monitor.school.value
        return RedirectResponse(url="/monitor", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="monitorLogin.html",
        context=login_context("Invalid area, institution, or password."),
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
        },
    )

@app.get("/dutyDashboard")
def duty_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="monitorDuty.html",
    )
