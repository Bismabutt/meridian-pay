# meridian-pay

Meridian Pay backend services.

## Services

| Service | Port | Language |
|---|---|---|
| api-gateway | 8000 | Python |
| auth-service | 8001 | Python |
| account-service | 8002 | Python |
| payment-service | 8004 | Python |
| ledger-service | 8005 | Go |
| fraud-service | 8006 | Python |
| fx-service | 8007 | Python |
| notification-service | 8008 | Python |

## Running locally

You need Postgres 15, Redis and Kafka running. Ask Amir for the setup script.

Create the databases:

```
createdb auth_db account_db payment_db ledger_db fraud_db fx_db notif_db
```

Then run the migrations in each service's `migrations/` folder, in order.

For each Python service:

```
cd services/auth-service
pip install -r requirements.txt
python -m app.main
```

For the ledger:

```
cd services/ledger-service
go run main.go
```

## Sandboxes

The partner bank, identity provider, FX feed and email provider all have
sandboxes under `sandboxes/`. Run them the same way. Nothing in dev should ever
point at the real partner rails.

## Seeding test data

```
python scripts/seed_data.py --profile small
```

Never copy production data into a test environment. Generate it.

## Notes

- Amounts are always integers in minor units (pence). Do not use floats.
- The ledger is append-only. Do not write UPDATE or DELETE against ledger_entries.
- Deploys are currently manual. Talk to Amir before pushing anything to prod.
