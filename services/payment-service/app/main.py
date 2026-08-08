"""payment-service — executes payments.

Sits inside the money zone. Talks to the ledger and the partner bank, and is the
only service permitted to instruct either.
"""
import json
import logging
import uuid
from datetime import datetime, timezone

import httpx
import redis
from fastapi import FastAPI, HTTPException

from app.config import settings
from app.db import query, get_conn, put_conn
from app.models import PaymentRequest, PaymentResponse
from app.partner_bank import submit_payment, PartnerBankError

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Meridian Pay — payment-service", version="3.0.1")

rds = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}


def _idempotency_lookup(key: str):
    cached = rds.get(f"idem:{key}")
    if cached:
        return json.loads(cached)
    row = query(
        """SELECT id, state, amount_minor, currency, partner_reference
             FROM payments WHERE idempotency_key = %s""",
        (key,), fetch="one",
    )
    return dict(row) if row else None


def _write_ledger_entries(payment_id: str, debtor_profile_id: str,
                          amount_minor: int, currency: str):
    with httpx.Client(timeout=5.0) as client:
        resp = client.post(
            f"{settings.LEDGER_SERVICE_URL}/v1/ledger/entries",
            json={
                "transaction_id": str(uuid.uuid4()),
                "payment_id": payment_id,
                "legs": [
                    {"account_id": debtor_profile_id, "direction": "debit",
                     "amount_minor": amount_minor, "currency": currency},
                    {"account_id": "SETTLEMENT", "direction": "credit",
                     "amount_minor": amount_minor, "currency": currency},
                ],
            },
        )
    if resp.status_code != 201:
        raise HTTPException(status_code=503, detail="Ledger write failed")
    return resp.json()


@app.post("/v1/payments", response_model=PaymentResponse, status_code=201)
def create_payment(req: PaymentRequest):
    # 1. Idempotency — a duplicate must never move money twice
    existing = _idempotency_lookup(req.idempotency_key)
    if existing:
        log.info("duplicate suppressed key=%s payment=%s", req.idempotency_key, existing["id"])
        return PaymentResponse(**existing)

    payment_id = str(uuid.uuid4())

    # 2. Record the instruction before doing anything irreversible
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO payments (id, idempotency_key, debtor_profile_id,
                       creditor_sort_code, creditor_account_number, creditor_name,
                       amount_minor, currency, reference, state, created_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending',NOW())""",
                (payment_id, req.idempotency_key, req.debtor_profile_id,
                 req.creditor_sort_code, req.creditor_account_number, req.creditor_name,
                 req.amount_minor, req.currency, req.reference),
            )
            cur.execute(
                """INSERT INTO outbox_events (id, payment_id, event_type, payload, created_at)
                   VALUES (%s,%s,'payment.initiated',%s,NOW())""",
                (str(uuid.uuid4()), payment_id,
                 json.dumps({"payment_id": payment_id,
                             "debtor_profile_id": req.debtor_profile_id,
                             "amount_minor": req.amount_minor,
                             "currency": req.currency})),
            )
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)

    # 3. Ledger is authoritative — it must record the movement before we confirm
    _write_ledger_entries(payment_id, req.debtor_profile_id, req.amount_minor, req.currency)

    # 4. Instruct the partner bank
    partner_reference = None
    state = "submitted"
    try:
        result = submit_payment(payment_id, req.creditor_sort_code,
                                req.creditor_account_number, req.creditor_name,
                                req.amount_minor, req.currency)
        partner_reference = result.get("payment_reference")
        state = "cleared"
    except PartnerBankError as exc:
        # Partner unavailable — the payment waits and is retried. It is never dropped.
        log.error("partner bank failure payment=%s: %s", payment_id, exc)
        state = "pending"

    query(
        "UPDATE payments SET state = %s, partner_reference = %s WHERE id = %s",
        (state, partner_reference, payment_id), fetch=None,
    )
    query(
        """INSERT INTO payment_attempts (id, payment_id, attempt_no, partner_response, attempted_at)
           VALUES (%s,%s,1,%s,NOW())""",
        (str(uuid.uuid4()), payment_id, partner_reference or "no response"), fetch=None,
    )

    response = {"id": payment_id, "state": state, "amount_minor": req.amount_minor,
                "currency": req.currency, "partner_reference": partner_reference}
    rds.setex(f"idem:{req.idempotency_key}", 86400, json.dumps(response))
    return PaymentResponse(**response)


@app.get("/v1/payments/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: str):
    row = query(
        """SELECT id, state, amount_minor, currency, partner_reference
             FROM payments WHERE id = %s""",
        (payment_id,), fetch="one",
    )
    if not row:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentResponse(**row)


@app.get("/v1/payments")
def list_payments(profile_id: str, limit: int = 50):
    return {"payments": query(
        """SELECT id, state, amount_minor, currency, created_at
             FROM payments WHERE debtor_profile_id = %s
            ORDER BY created_at DESC LIMIT %s""",
        (profile_id, limit),
    )}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
