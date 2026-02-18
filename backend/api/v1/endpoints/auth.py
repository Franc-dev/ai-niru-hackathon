"""
Authentication endpoints.
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from backend.api.deps import get_current_user
from backend.core.security import create_access_token, get_password_hash, verify_password
from backend.repositories.user_repo import (
    create_user,
    get_user_by_email,
    update_user_preferred_language,
)


router = APIRouter()


LanguageCode = Literal["en", "sw"]


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    preferred_language: LanguageCode = "en"


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=64)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Invalid email address")
        return email


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Invalid email address")
        return email


class LanguageUpdateRequest(BaseModel):
    preferred_language: LanguageCode


@router.post("/signup", response_model=AuthResponse)
async def signup(payload: SignupRequest):
    """Create account and return bearer token."""
    existing_user = await get_user_by_email(payload.email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = await create_user(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        display_name=payload.display_name.strip() if payload.display_name else None,
    )
    token = create_access_token(user["id"])
    return AuthResponse(access_token=token, user=UserResponse(**user))


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest):
    """Authenticate and return bearer token."""
    user_doc = await get_user_by_email(payload.email)
    if not user_doc or not verify_password(payload.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    user = {
        "id": str(user_doc["_id"]),
        "email": user_doc.get("email", ""),
        "display_name": user_doc.get("display_name"),
        "preferred_language": user_doc.get("preferred_language", "en"),
    }
    token = create_access_token(user["id"])
    return AuthResponse(access_token=token, user=UserResponse(**user))


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user)):
    """Return current user profile."""
    return UserResponse(**current_user)


@router.patch("/me/language", response_model=UserResponse)
async def update_language(
    payload: LanguageUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update current user preferred language."""
    await update_user_preferred_language(current_user["id"], payload.preferred_language)
    current_user["preferred_language"] = payload.preferred_language
    return UserResponse(**current_user)
