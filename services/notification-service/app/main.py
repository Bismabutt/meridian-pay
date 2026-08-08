"""notification-service — transactional email and push.

Tier 3. Explicitly permitted to lag. Consumes Kafka events so that email
provider latency never becomes payment latency.
"""
import json
import logging
import threading
import uuid

import httpx
from fastapi import FastAPI
from kafka import KafkaConsumer

from app.config import settings
from app.db import query

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Meridian Pay — notification-service", version="1.1.0")

TEMPLATES = {
    "payment.cleared": "Your payment of {amount} {currency} has been sent.",
    "payment.failed": "We could not send your payment of {amount} {currency}.",
    "customer.onboarded": "Welcome to Meridian Pay.",
}


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}


def already_delivered(event_id: str) -> bool:
    """Kafka may deliver the same event twice. The customer gets one email."""
    return query(
        "SELECT id FROM notification_log WHERE event_id = %s", (event_id,), fetch="one"
    ) is not None


def send(event_type: str, event):
    event_id = event.get("event_id") or event.get("payment_id")
    if already_delivered(event_id):
        log.info("duplicate event suppressed %s", event_id)
        return

    body = TEMPLATES.get(event_type, "Account update").format(
        amount=event.get("amount_minor", 0) / 100,
        currency=event.get("currency", "GBP"),
    )

    delivered = False
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{settings.EMAIL_PROVIDER_URL}/v1/send",
                headers={"Authorization": f"Bearer {settings.EMAIL_PROVIDER_KEY}"},
                json={"to": event.get("email", "customer@example.com"),
                      "subject": "Meridian Pay", "body": body},
            )
            delivered = resp.status_code < 300
    except Exception as exc:
        log.error("email provider failure: %s", exc)

    query(
        """INSERT INTO notification_log (id, event_id, event_type, channel, body, delivered_at)
           VALUES (%s,%s,%s,'email',%s,%s)""",
        (str(uuid.uuid4()), event_id, event_type, body,
         "NOW()" if delivered else None), fetch=None,
    )


def consume():
    consumer = KafkaConsumer(
        "payment.cleared", "payment.failed", "customer.onboarded",
        bootstrap_servers=settings.KAFKA_BOOTSTRAP,
        group_id="notification-service",
        auto_offset_reset="earliest",
        value_deserializer=lambda m: json.loads(m.decode()),
    )
    log.info("notification consumer started")
    for message in consumer:
        try:
            send(message.topic, message.value)
        except Exception as exc:
            log.error("notification failed: %s", exc)


@app.on_event("startup")
def start_consumer():
    threading.Thread(target=consume, daemon=True).start()


@app.get("/v1/notifications")
def list_notifications(limit: int = 100):
    return {"notifications": query(
        """SELECT id, event_type, channel, delivered_at
             FROM notification_log ORDER BY id DESC LIMIT %s""", (limit,))}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
