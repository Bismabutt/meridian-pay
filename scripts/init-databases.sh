#!/bin/bash
set -e

for db in auth_db account_db payment_db ledger_db fraud_db fx_db notif_db; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-EOSQL
    CREATE DATABASE $db;
EOSQL
done
