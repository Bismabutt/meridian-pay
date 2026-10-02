#!/usr/bin/env python3
"""Apply schema migrations to the RDS instances.

Locally the databases run as a single Postgres pod and migrations are piped
in with kubectl exec. On AWS each service has its own RDS instance outside
the cluster, so migrations are applied from here instead.

Endpoints come from Terraform outputs and credentials from Secrets Manager,
so nothing is typed and no password appears in this file.

Usage:
    python scripts/migrate.py
    python scripts/migrate.py --dry-run
"""
import argparse
import json
import os
import subprocess
import sys

import psycopg2

TERRAFORM_DIR = "infrastructure/terraform/environments/dev"

# service directory -> RDS instance key in the Terraform output
SERVICES = {
    "auth-service": "auth",
    "account-service": "account",
    "payment-service": "payment",
    "ledger-service": "ledger",
    "fraud-service": "fraud",
    "fx-service": "fx",
    "notification-service": "notification",
}


def terraform_output(name: str):
    """Read a named output from the dev environment."""
    result = subprocess.run(
        ["terraform", f"-chdir={TERRAFORM_DIR}", "output", "-json", name],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Could not read terraform output '{name}'.", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def secret_value(secret_name: str) -> dict:
    """Read a secret from Secrets Manager and return it parsed."""
    result = subprocess.run(
        [
            "aws", "secretsmanager", "get-secret-value",
            "--secret-id", secret_name,
            "--region", "eu-west-2",
            "--query", "SecretString",
            "--output", "text",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Could not read secret '{secret_name}'.", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout.strip())


def apply_migration(host: str, dbname: str, user: str, password: str,
                    sql_path: str, dry_run: bool):
    if not os.path.exists(sql_path):
        print(f"  no migration file at {sql_path}, skipping")
        return

    with open(sql_path) as f:
        sql = f.read()

    statements = [s.strip() for s in sql.split(";") if s.strip()]
    print(f"  {len(statements)} statements in {os.path.basename(sql_path)}")

    if dry_run:
        print("  dry run, nothing applied")
        return

    conn = psycopg2.connect(
        host=host, port=5432, dbname=dbname,
        user=user, password=password, connect_timeout=15,
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        print("  applied")
    finally:
        conn.close()


def verify(host: str, dbname: str, user: str, password: str):
    """List the tables that now exist, so the result is checked not assumed."""
    conn = psycopg2.connect(
        host=host, port=5432, dbname=dbname,
        user=user, password=password, connect_timeout=15,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            )
            tables = [r[0] for r in cur.fetchall()]
        print(f"  tables: {', '.join(tables) if tables else 'none'}")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would be applied without applying it")
    args = parser.parse_args()

    print("Reading database endpoints from Terraform...")
    endpoints = terraform_output("database_endpoints")
    print(f"Found {len(endpoints)} instances\n")

    failures = []

    for service_dir, db_key in SERVICES.items():
        print(f"{service_dir}")

        host = endpoints.get(db_key)
        if not host:
            print(f"  no endpoint for '{db_key}' in terraform output, skipping")
            failures.append(service_dir)
            continue

        secret = secret_value(f"meridian-pay-dev/rds/{db_key}")
        dbname = secret.get("dbname", db_key.replace("-", "_"))
        user = secret["username"]
        password = secret["password"]

        sql_path = os.path.join("services", service_dir, "migrations", "001_init.sql")

        try:
            apply_migration(host, dbname, user, password, sql_path, args.dry_run)
            if not args.dry_run:
                verify(host, dbname, user, password)
        except Exception as exc:
            print(f"  FAILED: {exc}")
            failures.append(service_dir)

        print()

    if failures:
        print(f"Failed: {', '.join(failures)}")
        sys.exit(1)

    print("All migrations applied.")


if __name__ == "__main__":
    main()
