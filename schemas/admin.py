from pydantic import BaseModel, EmailStr
from models.schools import School

class AdminLogin(BaseModel):
    email: EmailStr
    password: str
    school: School