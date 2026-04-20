from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from redis import Redis

from .config import settings

Role = Literal["viewer", "verifier", "admin"]

bearer_scheme = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def _encode_token(subject: str, role: Role, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    jti = str(uuid4())
    payload = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def create_access_token(subject: str, role: Role) -> str:
    return _encode_token(subject, role, "access", timedelta(minutes=settings.JWT_EXPIRE_MINUTES))


def create_refresh_token(subject: str, role: Role) -> str:
    return _encode_token(subject, role, "refresh", timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS))


def create_token_pair(subject: str, role: Role) -> dict:
    return {
        "access_token": create_access_token(subject, role),
        "refresh_token": create_refresh_token(subject, role),
        "token_type": "bearer",
    }


def revoke_token(jti: str, exp_ts: int):
    ttl = max(0, exp_ts - int(datetime.now(timezone.utc).timestamp()))
    if ttl > 0:
        redis_client.setex(f"{settings.TOKEN_REVOKE_PREFIX}:{jti}", ttl, "1")


def is_token_revoked(jti: str) -> bool:
    return redis_client.exists(f"{settings.TOKEN_REVOKE_PREFIX}:{jti}") == 1


def decode_token(token: str, expected_type: str | None = None) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        if expected_type and payload.get("type") != expected_type:
            raise HTTPException(status_code=401, detail="Invalid token type")
        if is_token_revoked(payload.get("jti", "")):
            raise HTTPException(status_code=401, detail="Token revoked")
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")
    return decode_token(credentials.credentials, expected_type="access")


def require_roles(*roles: Role):
    def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return _checker