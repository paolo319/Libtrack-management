from pydantic import BaseModel, EmailStr

class MonitorLogin(BaseModel):
    email: EmailStr
    password: str
