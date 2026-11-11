from pydantic import BaseModel, ConfigDict, Field

class MonitorLogin(BaseModel):
    """Monitor login submitted from monitorLogin.html.

    The form posts `userArea` / `userSchool`; the aliases keep those field
    names working while the model uses readable names internally.
    """

    model_config = ConfigDict(populate_by_name=True)

    area: str = Field(validation_alias="userArea")
    school: str = Field(validation_alias="userSchool")
    password: str
