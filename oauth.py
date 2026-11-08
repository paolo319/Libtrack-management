from pwdlib import PasswordHash
from datetime import datetime, timedelta, timezone
from app.config import settings
import jwt


pwd = PasswordHash.recommended()
ALGORITHM = "HS256"

def hash_password(plain_password:str)->str:
    return pwd.hash(plain_password)
def verify_password(plain_password: str,hashed_password: str)->bool:
    return pwd.verify(plain_password,hashed_password)

# def hash_otp(plain_otp: str):
#     return pwd.hash(plain_otp)
# def verify_otp(plain_otp: str,hashed_otp: str)->bool:
#     return pwd.verify(plain_otp,hashed_otp)


def create_access_token(user_id: int,user_type:str, expires_hour:int)->str:
    expire = datetime.now(timezone.utc) + timedelta(hours=expires_hour)
    payload = {
        "sub": str(user_id),
        "type": user_type,
        "exp": expire
    }
    return jwt.encode(payload,settings.JWT_SECRET_KEY,algorithm=ALGORITHM)

def decode_access_token(token:str)->dict:
    return jwt.decode(token,settings.JWT_SECRET_KEY,algorithms=[ALGORITHM])
