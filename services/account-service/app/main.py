"""account-service — profiles, virtual accounts, balance views.

Highest read volume in the platform. Balance projections are maintained from
ledger events; the ledger remains authoritative for anything that moves money.
"""
import logging
import random
import uuid

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.db import query

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Meridian Pay — account-service", version="2.1.0")


class ProfileCreate(BaseModel):
    user_id: str
    trading_name: str
    address: str


class ProfileResponse(BaseModel):
    id: str
    user_id: str
    trading_name: str
    address: str
    account_status: str


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}


def _allocate_virtual_account(profile_id: str):
    """Assign a sort code and account number from our partner bank's range."""
    sort_code = "04-00-53"
    for _ in range(5):
        account_number = str(random.randint(10000000, 99999999))
        clash = query(
            "SELECT id FROM virtual_accounts WHERE account_number = %s",
            (account_number,), fetch="one",
        )
        if clash:
            continue
        query(
            """INSERT INTO virtual_accounts (id, profile_id, sort_code, account_number, assigned_at)
               VALUES (%s, %s, %s, %s, NOW())""",
            (str(uuid.uuid4()), profile_id, sort_code, account_number), fetch=None,
        )
        return sort_code, account_number
    raise HTTPException(status_code=500, detail="Could not allocate a virtual account")


@app.post("/v1/accounts", response_model=ProfileResponse, status_code=201)
def create_profile(req: ProfileCreate):
    profile_id = str(uuid.uuid4())
    query(
        """INSERT INTO business_profiles (id, user_id, trading_name, address, account_status, created_at)
           VALUES (%s, %s, %s, %s, 'active', NOW())""",
        (profile_id, req.user_id, req.trading_name, req.address), fetch=None,
    )
    _allocate_virtual_account(profile_id)
    query(
        """INSERT INTO balance_projections (profile_id, available_minor, last_event_id, updated_at)
           VALUES (%s, 0, NULL, NOW())""",
        (profile_id,), fetch=None,
    )
    return ProfileResponse(id=profile_id, user_id=req.user_id,
                           trading_name=req.trading_name, address=req.address,
                           account_status="active")


@app.get("/v1/accounts/{profile_id}")
def get_profile(profile_id: str):
    profile = query(
        """SELECT p.id, p.user_id, p.trading_name, p.address, p.account_status,
                  v.sort_code, v.account_number
             FROM business_profiles p
             LEFT JOIN virtual_accounts v ON v.profile_id = p.id
            WHERE p.id = %s""",
        (profile_id,), fetch="one",
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Account not found")
    return profile


@app.get("/v1/accounts/{profile_id}/balance")
def get_balance(profile_id: str, authoritative: bool = False):
    """Dashboard reads use the projection. Money movement uses the ledger."""
    if authoritative:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{settings.LEDGER_SERVICE_URL}/v1/ledger/balance/{profile_id}")
            if resp.status_code != 200:
                raise HTTPException(status_code=503, detail="Ledger unavailable")
            return {"source": "ledger", **resp.json()}

    row = query(
        "SELECT available_minor, updated_at FROM balance_projections WHERE profile_id = %s",
        (profile_id,), fetch="one",
    )
    if not row:
        raise HTTPException(status_code=404, detail="Account not found")
    return {
        "source": "projection",
        "profile_id": profile_id,
        "available_minor": row["available_minor"],
        "currency": "GBP",
        "as_of": row["updated_at"],
    }


@app.get("/v1/accounts/lookup/{account_number}")
def lookup_by_account_number(account_number: str):
    """Used when funds arrive at the pooled account tagged with a virtual number."""
    row = query(
        "SELECT profile_id, sort_code, account_number FROM virtual_accounts WHERE account_number = %s",
        (account_number,), fetch="one",
    )
    if not row:
        raise HTTPException(status_code=404, detail="Unknown virtual account")
    return row


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
