from typing import Annotated

from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import HeadAdmin  


app = FastAPI()
templates = Jinja2Templates(directory="Templates")
Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return RedirectResponse(url="/libtrack", status_code=303)

@app.get("/libtrack")
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="headLogin.html")


@app.post("/libtrack")
def login(
    request: Request,
    userEmail: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: Session = Depends(get_db),
):
    head = db.query(HeadAdmin).filter(HeadAdmin.email == userEmail).first()

    if head and head.password == password:
        return RedirectResponse(url= "/headDashboard", status_code=303)
        

    return templates.TemplateResponse(
        request=request,
        name="headLogin.html",
        context={"error": "Invalid email or password"}
    )

@app.get("/headDashboard")
def monitor_page(request: Request):
    return templates.TemplateResponse(request=request, name="headDashboard.html")
    
    