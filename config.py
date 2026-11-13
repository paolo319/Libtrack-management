from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().with_name(".env")


class Settings(BaseSettings):
    database_hostname: str
    database_port: int
    database_password: str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    # class Config:
    #     env_file = ".env"
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        extra="ignore",
    )

    # Duty RFID bridge (device token is scoped to duty scanning only).
    duty_bridge_token: str | None = None
    duty_monitor_id: int | None = None
    duty_rate_limit_per_minute: int = 60
    duty_api_url: str = "http://127.0.0.1:8000"
    duty_serial_port: str = "COM4"
    duty_serial_baud: int = 9600

settings = Settings()
