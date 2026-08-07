from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from backend.config import LOGIN_PASSWORD, JWT_SECRET

ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30

bearer_scheme = HTTPBearer(auto_error=False)


def verify_password(password: str) -> bool:
    return password == LOGIN_PASSWORD


def create_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {"exp": expire, "sub": "user"}
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="需要登录")
    try:
        jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token 无效或已过期")
