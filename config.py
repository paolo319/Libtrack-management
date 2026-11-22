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

    # Duty scan rate limit.
    duty_rate_limit_per_minute: int = 60

settings = Settings()
