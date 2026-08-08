"""fraud-service — scores payment events consumed from Kafka.

This service never reads payment-db or ledger-db. It consumes notices about
payments, which is why it sits outside the money zone.
"""
import json
import logging
import threading
import uuid

from fastapi import FastAPI
from kafka import KafkaConsumer

from app.config import settings
from app.db import query
from app.rules import score_payment

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Meridian Pay — fraud-service", version="1.2.0")

CASE_THRESHOLD = 70


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}


def handle_payment_event(payment):
    score, hits = score_payment(payment)
    score_id = str(uuid.uuid4())

    query(
        """INSERT INTO fraud_scores (id, payment_id, account_id, score, rule_hits, scored_at)
           VALUES (%s,%s,%s,%s,%s,NOW())""",
        (score_id, payment["payment_id"], payment["debtor_profile_id"],
         score, json.dumps(hits)), fetch=None,
    )

    if score >= CASE_THRESHOLD:
        query(
            """INSERT INTO fraud_cases (id, score_id, account_id, state, created_at)
               VALUES (%s,%s,%s,'open',NOW())""",
            (str(uuid.uuid4()), score_id, payment["debtor_profile_id"]), fetch=None,
        )
        log.warning("case raised payment=%s score=%s", payment["payment_id"], score)

    return score


def consume():
    consumer = KafkaConsumer(
        "payment.initiated",
        bootstrap_servers=settings.KAFKA_BOOTSTRAP,
        group_id="fraud-service",
        auto_offset_reset="earliest",
        value_deserializer=lambda m: json.loads(m.decode()),
    )
    log.info("fraud consumer started")
    for message in consumer:
        try:
            handle_payment_event(message.value)
        except Exception as exc:
            log.error("scoring failed: %s", exc)


@app.on_event("startup")
def start_consumer():
    threading.Thread(target=consume, daemon=True).start()


@app.get("/v1/fraud/cases")
def list_cases(state: str = "open", limit: int = 100):
    return {"cases": query(
        """SELECT c.id, c.account_id, c.state, c.created_at, s.score, s.payment_id
             FROM fraud_cases c JOIN fraud_scores s ON s.id = c.score_id
            WHERE c.state = %s ORDER BY c.created_at DESC LIMIT %s""",
        (state, limit),
    )}


@app.get("/v1/fraud/scores/{payment_id}")
def get_score(payment_id: str):
    return query(
        "SELECT id, payment_id, score, rule_hits, scored_at FROM fraud_scores WHERE payment_id = %s",
        (payment_id,), fetch="one",
    ) or {"detail": "not scored yet"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
