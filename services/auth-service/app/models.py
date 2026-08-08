from pydantic import BaseModel, EmailStr
from typing import Optional


class RegisterRequest(BaseModel):
    company_name: str
    company_number: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    company_name: str
    company_number: str
    email: str
    status: str


class ApiKeyResponse(BaseModel):
    id: str
    api_key: Optional[str] = None
    rate_limit_tier: str
