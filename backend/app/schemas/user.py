"""User schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class UserCreate(BaseModel):
    username: str = Field(min_length=3, maxlength=32, pattern=r"^[a-zA-Z0-9.-]+$")
    display_name: str = Field(min_length=2, max_length=60)
    password: str = Field(min_length=6, max_length=72)

    @field_validator("username", "display_name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class UserLogin(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    id: int
    username: str
    display_name: str
    created_at: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic