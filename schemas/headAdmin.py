from pydantic import BaseModel, ConfigDict, EmailStr, Field

class HeadAdminLogin(BaseModel):
    """Head administrator login submitted from headLogin.html."""

    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr = Field(validation_alias="userEmail")
    password: str
