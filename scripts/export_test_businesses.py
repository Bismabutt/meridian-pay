#!/usr/bin/env python3
"""Export seeded test businesses for the k6 load scenarios.

The load tests measure payment throughput, so the businesses they act as
must already exist. This reads a sample of seeded accounts and writes the
credentials k6 needs.

All data here is synthetic. Passwords are generated for the test environment
and are not used anywhere else.

Usage:
    python scripts/export_test_businesses.py --count 50
"""
import argparse
import json
import os
import sys

import psycopg2
from psycopg2.extras import RealDictCursor

DEFAULT_OUTPUT = "load-tests/test-businesses.json"

SEED_PASSWORD = os.getenv("SEED_PASSWORD", "LoadTest2026!")


def fetch_businesses(count: int):
    auth_dsn = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "user": os.getenv("DB_USER", "meridian_app"),
        "password": os.getenv("DB_PASSWORD", ""),
        "dbname": "auth_db",
    }
    account_dsn = dict(auth_dsn, dbname="account_db")

    with psycopg2.connect(**auth_dsn) as auth_conn:
        with auth_conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, email, company_name
                FROM users
                WHERE status = 'active'
                ORDER BY created_at
                LIMIT %s
                """,
                (count,),
            )
            users = cur.fetchall()

    if not users:
        print("No seeded users found. Run seed_data.py first.", file=sys.stderr)
        sys.exit(1)

    user_ids = [u["id"] for u in users]

    with psycopg2.connect(**account_dsn) as acct_conn:
        with acct_conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT business_id, id AS account_id
                FROM virtual_accounts
                WHERE business_id = ANY(%s)
                  AND status = 'active'
                """,
                (user_ids,),
            )
            accounts = {a["business_id"]: a["account_id"] for a in cur.fetchall()}

    businesses = []
    for u in users:
        account_id = accounts.get(u["id"])
        if not account_id:
            continue
        businesses.append(
            {
                "email": u["email"],
                "password": SEED_PASSWORD,
                "business_id": str(u["id"]),
                "account_id": str(account_id),
                "company_name": u["company_name"],
            }
        )

    return businesses


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=50,
                        help="How many businesses to export")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    businesses = fetch_businesses(args.count)

    if not businesses:
        print("Found users but no active accounts for them.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(businesses, f, indent=2)

    print(f"Wrote {len(businesses)} businesses to {args.output}")


if __name__ == "__main__":
    main()