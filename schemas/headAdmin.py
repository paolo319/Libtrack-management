from pydantic import BaseModel, EmailStr

class HeadAdminLogin(BaseModel):
    email: EmailStr
    password: str
