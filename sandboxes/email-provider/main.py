"""Email provider sandbox — accepts and records messages, can be slowed down."""
import os
import time
import uuid

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Email Provider Sandbox")

STATE = {"available": True, "latency_ms": 200}
SENT = []


class Message(BaseModel):
    to: str
    subject: str
    body: str


@app.get("/health")
def health():
    return {"status": "ok" if STATE["available"] else "unavailable"}


@app.post("/admin/degrade")
def degrade(latency_ms: int = 200):
    """Used to demonstrate why notifications belong off the payment path."""
    STATE["latency_ms"] = latency_ms
    return STATE


@app.post("/v1/send")
def send(msg: Message):
    time.sleep(STATE["latency_ms"] / 1000)
    record = {"id": str(uuid.uuid4()), "to": msg.to, "subject": msg.subject}
    SENT.append(record)
    return record


@app.get("/v1/sent")
def sent(limit: int = 50):
    return {"count": len(SENT), "messages": SENT[-limit:]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "9103")))
