from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
