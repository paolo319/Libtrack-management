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
from models import Monitor
from router.dutyRoute import router as duty_router
from router.scannerRoute import router as scanner_router
from schemas import MonitorLogin
app = FastAPI()
app.add_middleware(
    SessionMiddleware, secret_key=settings.secret_key, same_site="strict"
)


@app.middleware("http")
async def cache_headers(request: Request, call_next):
    """Keep JS/CSS fresh and never cache the kiosk HTML pages."""
    response = await call_next(request)
    path = request.url.path
    if path.endswith((".js", ".css")):
        response.headers["Cache-Control"] = "no-cache"
    elif path in {"/", "/login", "/monitor", "/dutyDashboard"}:
        response.headers["Cache-Control"] = "no-store"
    return response


app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(scanner_router)
app.include_router(duty_router)
templates = Jinja2Templates(directory="Templates")

# Creates missing tables. Existing data is left untouched.
Base.metadata.create_all(bind=engine)


@app.get("/")
def landing_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="monitorLogin.html",
        context={"error": None},
    )


@app.post("/login")
def login(
    request: Request,
    form: Annotated[MonitorLogin, Form()],
    db: Session = Depends(get_db),
):
    area = form.area.strip().lower()
    email = str(form.email).strip().lower()

    monitor = (
        db.query(Monitor)
        .filter(
            func.lower(Monitor.area) == area,
            func.lower(Monitor.email) == email,
        )
        .first()
    )

    if monitor and monitor.password == form.password:
        request.session["monitor_id"] = monitor.id
        request.session["area"] = monitor.area
        request.session["monitor"] = monitor.email
        request.session["school"] = monitor.school.name
        request.session["school_logo"] = monitor.school.logo_url
        return RedirectResponse(url="/monitor", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="monitorLogin.html",
        context={"error": "Invalid area, email, or password."},
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