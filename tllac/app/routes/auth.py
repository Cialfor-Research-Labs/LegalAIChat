from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from ..db.db_client import db_client
from ..services.auth_service import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, str]


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    try:
        user = db_client.create_user(
            email=request.email,
            full_name=request.full_name,
            password=request.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return AuthResponse(access_token=create_access_token(user["user_id"]), user=user)


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    user = db_client.authenticate_user(request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    return AuthResponse(access_token=create_access_token(user["user_id"]), user=user)


@router.get("/me")
async def me(current_user: dict[str, str] = Depends(get_current_user)):
    return {"user": current_user}
