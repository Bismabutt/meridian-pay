"""Seed the platform with realistic data at production scale.

Generates business customers, virtual accounts, ledger history and payments.
Uses COPY rather than row-by-row inserts, because 40 million ledger entries
through individual INSERTs would take days.

Usage:
    python scripts/seed_data.py --profile small     # 10k accounts,   200k entries
    python scripts/seed_data.py --profile medium    # 100k accounts,  4M entries
    python scripts/seed_data.py --profile full      # 1.2M accounts, 40M entries
"""
import argparse
import io
import random
import uuid
from datetime import datetime, timedelta

import psycopg2

PROFILES = {
    "small":  {"accounts": 10_000,    "entries": 200_000,    "payments": 20_000},
    "medium": {"accounts": 100_000,   "entries": 4_000_000,  "payments": 200_000},
    "full":   {"accounts": 1_200_000, "entries": 40_000_000, "payments": 2_000_000},
}

PREFIXES = ["Northgate", "Ashford", "Blackwell", "Camden", "Dunmore", "Eastvale",
            "Fairhurst", "Glenmore", "Harrowgate", "Ivybridge", "Kelston",
            "Langford", "Merrivale", "Newbury", "Oakhampton", "Pendleton",
            "Quarrydown", "Ravenscroft", "Stanmore", "Thornbury", "Uppingham",
            "Vale Park", "Westbrook", "Yarmouth"]

SUFFIXES = ["Textiles", "Logistics", "Consulting", "Engineering", "Media",
            "Catering", "Joinery", "Print", "Systems", "Trading", "Interiors",
            "Recruitment", "Plumbing", "Security", "Analytics", "Foods",
            "Autocare", "Legal Services", "Design Studio", "Property"]

FORMS = ["Ltd", "Limited", "LLP", "& Co Ltd", "Group Ltd", "Services Ltd"]

CITIES = ["London", "Manchester", "Birmingham", "Leeds", "Glasgow", "Bristol",
          "Liverpool", "Sheffield", "Edinburgh", "Cardiff", "Nottingham",
          "Newcastle", "Southampton", "Leicester", "Belfast"]


def company_name(i):
    return f"{random.choice(PREFIXES)} {random.choice(SUFFIXES)} {random.choice(FORMS)}"


def connect(db_name):
    return psycopg2.connect(
        host="localhost", port=5432, dbname=db_name,
        user="meridian_app", password="MeridianDev2024!",
    )


def copy_from(conn, table, columns, rows):
    buf = io.StringIO()
    for row in rows:
        buf.write("\t".join("" if v is None else str(v) for v in row) + "\n")
    buf.seek(0)
    with conn.cursor() as cur:
        cur.copy_from(buf, table, columns=columns)
    conn.commit()


def seed_users_and_accounts(count, batch=50_000):
    print(f"Seeding {count:,} business customers...")
    auth = connect("auth_db")
    acct = connect("account_db")

    profile_ids = []
    used_numbers = set()

    for start in range(0, count, batch):
        n = min(batch, count - start)
        users, profiles, vaccounts, projections = [], [], [], []

        for i in range(n):
            uid = str(uuid.uuid4())
            pid = str(uuid.uuid4())
            name = company_name(start + i)
            created = datetime.now() - timedelta(days=random.randint(1, 1460))

            users.append((uid, name, f"{random.randint(10000000, 99999999)}",
                          f"accounts{start + i}@{name.split()[0].lower()}.co.uk",
                          "seed$0000000000000000000000000000000000000000000000000000000000000000",
                          "active", "verified", created))

            profiles.append((pid, uid, name,
                             f"{random.randint(1, 300)} High Street, {random.choice(CITIES)}",
                             "active", created))

            while True:
                acc_no = str(random.randint(10000000, 99999999))
                if acc_no not in used_numbers:
                    used_numbers.add(acc_no)
                    break
            vaccounts.append((str(uuid.uuid4()), pid, "04-00-53", acc_no, created))

            projections.append((pid, random.randint(50_000, 250_000_00), None, datetime.now()))
            profile_ids.append(pid)

        copy_from(auth, "users",
                  ("id", "company_name", "company_number", "email", "password_hash",
                   "status", "kyc_status", "created_at"), users)
        copy_from(acct, "business_profiles",
                  ("id", "user_id", "trading_name", "address", "account_status", "created_at"), profiles)
        copy_from(acct, "virtual_accounts",
                  ("id", "profile_id", "sort_code", "account_number", "assigned_at"), vaccounts)
        copy_from(acct, "balance_projections",
                  ("profile_id", "available_minor", "last_event_id", "updated_at"), projections)

        print(f"  {min(start + batch, count):,} / {count:,}")

    auth.close()
    acct.close()
    return profile_ids


def seed_ledger(profile_ids, entry_count, batch=200_000):
    print(f"Seeding {entry_count:,} ledger entries...")
    conn = connect("ledger_db")
    written = 0

    while written < entry_count:
        n = min(batch, entry_count - written)
        rows = []
        for _ in range(n // 2):
            txid = str(uuid.uuid4())
            account = random.choice(profile_ids)
            amount = random.choice([1250, 4999, 12500, 35000, 75000, 250000, 1000000])
            created = datetime.now() - timedelta(
                days=random.randint(0, 730), seconds=random.randint(0, 86400))
            rows.append((str(uuid.uuid4()), txid, account, "debit", amount, "GBP", None, created))
            rows.append((str(uuid.uuid4()), txid, "SETTLEMENT", "credit", amount, "GBP", None, created))

        copy_from(conn, "ledger_entries",
                  ("id", "transaction_id", "account_id", "direction",
                   "amount_minor", "currency", "payment_id", "created_at"), rows)
        written += len(rows)
        print(f"  {written:,} / {entry_count:,}")

    conn.close()


def seed_payments(profile_ids, count, batch=50_000):
    print(f"Seeding {count:,} payment records...")
    conn = connect("payment_db")
    states = ["cleared"] * 92 + ["pending"] * 4 + ["failed"] * 3 + ["submitted"]
    written = 0

    while written < count:
        n = min(batch, count - written)
        rows = []
        for _ in range(n):
            pid = str(uuid.uuid4())
            created = datetime.now() - timedelta(
                days=random.randint(0, 365), seconds=random.randint(0, 86400))
            rows.append((
                pid, f"idem-{uuid.uuid4()}", random.choice(profile_ids),
                "20-00-00", str(random.randint(10000000, 99999999)),
                company_name(0), random.randint(500, 5_000_000), "GBP",
                f"INV-{random.randint(1000, 99999)}", random.choice(states),
                "FPS" + uuid.uuid4().hex[:16].upper(), created,
            ))
        copy_from(conn, "payments",
                  ("id", "idempotency_key", "debtor_profile_id", "creditor_sort_code",
                   "creditor_account_number", "creditor_name", "amount_minor", "currency",
                   "reference", "state", "partner_reference", "created_at"), rows)
        written += n
        print(f"  {written:,} / {count:,}")

    conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=PROFILES.keys(), default="small")
    args = parser.parse_args()
    cfg = PROFILES[args.profile]

    started = datetime.now()
    print(f"Seeding profile: {args.profile}")
    print(f"  accounts: {cfg['accounts']:,}")
    print(f"  ledger entries: {cfg['entries']:,}")
    print(f"  payments: {cfg['payments']:,}\n")

    profile_ids = seed_users_and_accounts(cfg["accounts"])
    sample = random.sample(profile_ids, min(len(profile_ids), 50_000))
    seed_ledger(sample, cfg["entries"])
    seed_payments(sample, cfg["payments"])

    elapsed = (datetime.now() - started).total_seconds()
    print(f"\nDone in {elapsed:.0f}s")


if __name__ == "__main__":
    main()
