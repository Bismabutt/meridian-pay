# Architecture

## Trust zones

The platform is divided into five zones. The boundary between them is
enforced by network policy, not by convention.

```
┌─────────────────────────────────────────────────────────┐
│ 1. CUSTOMERS                                            │
│    Web application (humans)                             │
│    API integrations (machines)                          │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS
┌────────────────────────▼────────────────────────────────┐
│ 2. EDGE                          namespace: meridian-edge│
│    AWS ALB, TLS termination, WAF                        │
│    NGINX Ingress Controller                             │
│    api-gateway: authentication, rate limits, routing    │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ 3. APPLICATION ZONE               namespace: meridian-app│
│    auth-service      account-service                    │
│    fx-service        fraud-service                      │
│    notification-service                                 │
│    Redis (sessions, idempotency keys)                   │
└────────────────────────┬────────────────────────────────┘
                         │ only api-gateway and payment-service
                         │ may cross this boundary
┌────────────────────────▼────────────────────────────────┐
│ 4. MONEY ZONE                   namespace: meridian-money│
│    payment-service                                      │
│    ledger-service                                       │
│    DEFAULT DENY: nothing enters unless explicitly       │
│    permitted                                            │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ 5. EXTERNAL PARTNERS                                    │
│    Partner bank (BaaS, holds the pooled account)        │
│    Identity provider (KYC)                              │
│    FX rates provider                                    │
└─────────────────────────────────────────────────────────┘

Kafka runs in its own namespace under the Strimzi operator.
```

## Why zones rather than one flat namespace

Discovery finding 7: an analytics query was run directly against the
production ledger and degraded payment latency for an hour, because
everything could reach everything.

A namespace boundary with default deny makes that class of incident
structurally impossible rather than discouraged. A pod label is something
anyone can copy; a namespace with an explicit allow list is not.

---

## Payment request flow

```
Customer
   │ POST /v1/payments
   ▼
ALB                     TLS termination, WAF
   ▼
NGINX Ingress
   ▼
api-gateway             validate JWT, apply rate limit, route
   ▼
payment-service         ── Redis: idempotency key check ──┐
   │                                                       │
   │                    if key seen before, return the     │
   │                    original result without moving money
   ▼
ledger-service          write balanced double entry
   │                    debit customer, credit settlement
   │                    both legs, one transaction, sums to zero
   ▼
partner bank            submit the instruction
   │                    if unavailable: queue and retry,
   │                    never reject
   ▼
"Success" to the customer

Asynchronously, via Kafka:
   payment.initiated ──▶ fraud-service    (scoring)
   payment.cleared   ──▶ notification-service (email)
```

## Synchronous versus asynchronous

**Synchronous, in the customer's request path:** idempotency check, ledger
write, partner submission. These determine whether the payment succeeded, so
the customer waits for them.

**Asynchronous, via Kafka:** fraud scoring and notifications. A delayed fraud
score or a delayed email does not change whether money moved. Making these
synchronous would add latency to every payment for no correctness benefit.

---

## The outbox pattern

payment-service writes the payment record and the event to be published in
the same database transaction, to a table called `outbox_events`. A separate
process reads that table and publishes to Kafka.

**Why:** if the service wrote to the database and then published to Kafka as
two separate operations, a crash between them would leave a payment with no
event, or an event with no payment. Writing both in one transaction removes
that window.

---

## Idempotency

Every payment request carries an idempotency key supplied by the client.

**Two layers of protection:**

1. Redis holds recently seen keys. A repeat within the window returns the
   original result without touching the ledger.
2. `payments.idempotency_key` carries a unique constraint in PostgreSQL. If
   Redis misses, the database refuses the duplicate.

**Why two:** Redis is fast but not durable. The database constraint is the
guarantee; Redis is the optimisation.

---

## Partner failure handling

Each external dependency fails differently, so each is handled differently.

| Dependency | On failure | Reasoning |
|---|---|---|
| Partner bank | Queue and retry | A rejected customer submits again, which creates duplicates |
| Identity provider | Delay onboarding | A new customer waiting is acceptable; an existing customer blocked is not |
| FX rates provider | Serve stale rates with visible age | A slightly old rate is better than no service. Staleness is a business decision |

---

## Architecture decision records

| ADR | Decision |
|---|---|
| [ADR-001](adr/ADR-001-ingress-vs-api-gateway.md) | NGINX Ingress Controller rather than AWS API Gateway |
| [ADR-002](adr/ADR-002-kafka-strimzi-vs-msk.md) | Kafka self managed via Strimzi rather than MSK |
| [ADR-003](adr/ADR-003-managed-rds.md) | Managed RDS rather than PostgreSQL in the cluster |
| [ADR-004](adr/ADR-004-single-nat-gateway.md) | One NAT gateway in non production |
| [ADR-005](adr/ADR-005-spot-capacity.md) | Spot capacity for dev worker nodes |
| [ADR-006](adr/ADR-006-for-each-over-count.md) | for_each rather than count for per service resources |
| [ADR-007](adr/ADR-007-generated-credentials.md) | Generated credentials in Secrets Manager |
