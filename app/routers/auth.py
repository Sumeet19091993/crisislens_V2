from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import create_token_pair, decode_token, hash_password, revoke_token, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class RegisterIn(BaseModel):
    username: str
    password: str
    role: str = "viewer"


class LoginIn(BaseModel):
    username: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class LogoutIn(BaseModel):
    token: str


@router.post("/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    exists = db.scalar(select(User).where(User.username == payload.username))
    if exists:
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": str(user.id), "username": user.username, "role": user.role}


@router.post("/token")
def token(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User inactive")
    return create_token_pair(user.username, user.role)


@router.post("/refresh")
def refresh(payload: RefreshIn):
    claims = decode_token(payload.refresh_token, expected_type="refresh")
    return create_token_pair(claims["sub"], claims["role"])


@router.post("/logout")
def logout(payload: LogoutIn):
    claims = decode_token(payload.token, expected_type=None)
    revoke_token(claims["jti"], claims["exp"])
    return {"status": "logged_out", "at": datetime.now(timezone.utc).isoformat()}