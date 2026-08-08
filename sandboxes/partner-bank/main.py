"""Partner bank sandbox.

Stands in for the BaaS provider. Supports being taken offline on demand so the
partner outage drill can be run without touching a real provider.
"""
import os
import random
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Partner Bank Sandbox")

STATE = {"available": True, "latency_ms": 120, "failure_rate": 0.0}
POOLED_BALANCE_MINOR = 40_000_000_000  # GBP 400m held in the safeguarding account


class Amount(BaseModel):
    minor_units: int
    currency: str = "GBP"


class Creditor(BaseModel):
    sort_code: str
    account_number: str
    name: str


class PaymentInstruction(BaseModel):
    instruction_id: str
    creditor: Creditor
    amount: Amount


@app.get("/health")
def health():
    return {"status": "ok" if STATE["available"] else "unavailable"}


@app.post("/admin/outage")
def set_outage(enabled: bool):
    """Used by the drill scripts to simulate a partner outage."""
    STATE["available"] = not enabled
    return {"available": STATE["available"]}


@app.post("/admin/degrade")
def degrade(latency_ms: int = 120, failure_rate: float = 0.0):
    STATE["latency_ms"] = latency_ms
    STATE["failure_rate"] = failure_rate
    return STATE


@app.post("/v1/payments", status_code=201)
def submit(instruction: PaymentInstruction):
    if not STATE["available"]:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    if random.random() < STATE["failure_rate"]:
        raise HTTPException(status_code=502, detail="Upstream rails timeout")
    return {
        "payment_reference": "FPS" + uuid.uuid4().hex[:16].upper(),
        "instruction_id": instruction.instruction_id,
        "status": "accepted",
        "accepted_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/accounts/pooled/balance")
def pooled_balance():
    """Used by the daily reconciliation job."""
    return {"balance_minor": POOLED_BALANCE_MINOR, "currency": "GBP",
            "as_of": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "9100")))
