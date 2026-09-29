"""Payment-service metrics.

These are the business signals the dashboard is built from: how many
payments are succeeding, how long a customer waits, and how many are
queued because the partner bank is unavailable.
"""
from prometheus_client import Counter, Histogram, Gauge

# ------------------------------------------------------------
# Payment outcomes
# ------------------------------------------------------------

payments_total = Counter(
    "payments_total",
    "Payments by outcome",
    ["status"],   # accepted | cleared | failed | duplicate_suppressed
)

payment_amount_minor_total = Counter(
    "payment_amount_minor_total",
    "Cumulative payment value in minor units",
    ["status"],
)

# ------------------------------------------------------------
# Customer-visible latency
#
# Measures the full synchronous path: idempotency check, ledger write,
# partner submission. This is what the customer waits for.
# ------------------------------------------------------------

payment_duration_seconds = Histogram(
    "payment_duration_seconds",
    "End to end time to accept a payment, as experienced by the customer",
    buckets=(0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1.0, 2.0, 5.0, 10.0),
)

# ------------------------------------------------------------
# Payments waiting on the partner bank
#
# Flat at zero in normal operation. Climbs during a partner outage and
# drains when the partner recovers. Proves no payment is lost.
# ------------------------------------------------------------

payments_pending = Gauge(
    "payments_pending",
    "Payments accepted but not yet submitted to the partner bank",
)

payment_oldest_pending_seconds = Gauge(
    "payment_oldest_pending_seconds",
    "Age of the oldest payment still waiting on the partner bank",
)

# ------------------------------------------------------------
# Partner bank dependency
# ------------------------------------------------------------

partner_bank_requests_total = Counter(
    "partner_bank_requests_total",
    "Requests to the partner bank by outcome",
    ["outcome"],   # success | failure | retry
)

partner_bank_duration_seconds = Histogram(
    "partner_bank_duration_seconds",
    "Time taken by the partner bank to accept an instruction",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 8.0),
)

partner_bank_available = Gauge(
    "partner_bank_available",
    "Whether the partner bank is currently reachable, 1 or 0",
)

# ------------------------------------------------------------
# Idempotency
#
# A non-zero rate here is the duplicate-payment guard doing its job.
# ------------------------------------------------------------

idempotency_hits_total = Counter(
    "idempotency_hits_total",
    "Duplicate payment requests suppressed before money moved",
    ["source"],   # redis | database
)
