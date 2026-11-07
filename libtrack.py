from typing import Annotated

from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse
# from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Admin
from models import Monitor

app = FastAPI()
# app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="Templates")

# Creates missing tables. Existing data is left untouched.
Base.metadata.create_all(bind=engine)


@app.get("/")
def landing_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


@app.post("/login")
def login(
    request: Request,
    userArea: Annotated[str, Form()],
    userSchool: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: Session = Depends(get_db),
):
    monitor = db.query(Monitor).filter(Monitor.area == userArea, Monitor.school == userSchool).first()

    if monitor and monitor.password == password:
        return RedirectResponse(url= "/monitor", status_code=303)

    return templates.TemplateResponse(
        request=request,
        url="/login",
    )

@app.get("/monitor")
def monitor_page(request: Request):
    return templates.TemplateResponse(request=request, name="monitor.html")
    
    