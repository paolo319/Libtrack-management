from datetime import datetime, timedelta, timezone

import jwt

from config import settings

def access_token(data: dict) -> str:
    now = datetime.now(timezone.utc)
    payload = data.copy()
    payload["iat"] = now
    payload["exp"] = now + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def verify_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
