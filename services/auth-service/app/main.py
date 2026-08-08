"""auth-service — identity, login, JWT issuance, API keys, KYC onboarding."""
import logging
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException, Header, Depends

from app.config import settings
from app.db import query
from app.models import RegisterRequest, LoginRequest, TokenResponse, UserResponse, ApiKeyResponse
from app.security import (
    hash_password, verify_password, create_access_token,
    decode_token, generate_api_key,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Meridian Pay — auth-service", version="1.4.2")


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}


@app.post("/v1/auth/register", response_model=UserResponse, status_code=201)
def register(req: RegisterRequest):
    existing = query("SELECT id FROM users WHERE email = %s", (req.email,), fetch="one")
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # KYC check with the external identity provider
    kyc_status = "pending"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{settings.IDENTITY_PROVIDER_URL}/v1/verify",
                headers={"Authorization": f"Bearer {settings.IDENTITY_PROVIDER_KEY}"},
                json={"company_number": req.company_number, "company_name": req.company_name},
            )
            if resp.status_code == 200:
                kyc_status = resp.json().get("status", "pending")
    except Exception as exc:
        log.warning("KYC provider unavailable: %s", exc)

    user_id = str(uuid.uuid4())
    query(
        """INSERT INTO users (id, company_name, company_number, email, password_hash,
                              status, kyc_status, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (user_id, req.company_name, req.company_number, req.email,
         hash_password(req.password), "active", kyc_status, datetime.now(timezone.utc)),
        fetch=None,
    )
    return UserResponse(id=user_id, company_name=req.company_name,
                        company_number=req.company_number, email=req.email, status="active")


@app.post("/v1/auth/login", response_model=TokenResponse)
def login(req: LoginRequest):
    user = query(
        "SELECT id, email, password_hash, status FROM users WHERE email = %s",
        (req.email,), fetch="one",
    )
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user["status"] != "active":
        raise HTTPException(status_code=403, detail="Account is not active")

    session_id = str(uuid.uuid4())
    query(
        """INSERT INTO sessions (id, user_id, issued_at, expires_at)
           VALUES (%s, %s, NOW(), NOW() + INTERVAL '60 minutes')""",
        (session_id, user["id"]), fetch=None,
    )
    token = create_access_token(str(user["id"]), user["email"])
    log.info("login ok user=%s session=%s", user["id"], session_id)
    return TokenResponse(access_token=token, expires_in=settings.JWT_EXPIRY_MINUTES * 60)


@app.get("/v1/auth/verify")
def verify(authorization: str = Header(None)):
    """Called by api-gateway on every request."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        payload = decode_token(authorization.split(" ", 1)[1])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"user_id": payload["sub"], "email": payload["email"]}


@app.post("/v1/auth/api-keys", response_model=ApiKeyResponse, status_code=201)
def create_api_key(user_id: str, tier: str = "standard"):
    raw, key_hash = generate_api_key()
    key_id = str(uuid.uuid4())
    query(
        """INSERT INTO api_keys (id, user_id, key_hash, rate_limit_tier, created_at)
           VALUES (%s, %s, %s, %s, NOW())""",
        (key_id, user_id, key_hash, tier), fetch=None,
    )
    return ApiKeyResponse(id=key_id, api_key=raw, rate_limit_tier=tier)


@app.get("/v1/auth/users/search")
def search_users(company: str):
    """Internal ops search. Used by the support team."""
    sql = "SELECT id, company_name, email, status FROM users WHERE company_name LIKE '%" + company + "%' LIMIT 50"
    return {"results": query(sql)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
