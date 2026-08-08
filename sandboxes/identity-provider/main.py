"""Identity provider sandbox — KYC verification for business onboarding."""
import os
import random

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Identity Provider Sandbox")

STATE = {"available": True}


class VerifyRequest(BaseModel):
    company_number: str
    company_name: str


@app.get("/health")
def health():
    return {"status": "ok" if STATE["available"] else "unavailable"}


@app.post("/admin/outage")
def set_outage(enabled: bool):
    STATE["available"] = not enabled
    return {"available": STATE["available"]}


@app.post("/v1/verify")
def verify(req: VerifyRequest):
    if not STATE["available"]:
        return {"status": "pending", "reason": "provider unavailable"}
    verified = not req.company_number.startswith("00000")
    return {
        "status": "verified" if verified else "rejected",
        "company_number": req.company_number,
        "risk_rating": random.choice(["low", "low", "low", "medium"]),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "9101")))
