from pydantic import BaseModel, ConfigDict, EmailStr, Field

class MonitorLogin(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    area: str = Field(validation_alias="userArea")
    email: EmailStr = Field(validation_alias="userEmail")
    password: str
