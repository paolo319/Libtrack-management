from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_hostname: str
    database_port: int
    database_password: str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    # Duty RFID bridge (device token is scoped to duty scanning only).
    duty_bridge_token: str | None = None
    duty_monitor_id: int | None = None
    duty_rate_limit_per_minute: int = 60

    # class Config:
    #     env_file = ".env"
    model_config = SettingsConfigDict(
    env_file=".env",
    extra="ignore"
    )

settings = Settings()
