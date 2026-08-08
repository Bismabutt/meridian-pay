"""Fraud scoring rules.

Each rule returns (points, reason) or None. Scores accumulate; anything at or
above 70 is raised as a case for compliance review.
"""
from datetime import datetime, timezone

from app.config import settings
from app.db import query


def high_value(payment):
    if payment["amount_minor"] >= settings.HIGH_VALUE_THRESHOLD_MINOR:
        return 40, "amount at or above high value threshold"
    return None


def unusual_hour(payment):
    hour = datetime.now(timezone.utc).hour
    if hour < 6 or hour >= 23:
        return 15, "payment outside normal business hours"
    return None


def velocity(payment):
    row = query(
        """SELECT COUNT(*) AS c FROM fraud_scores
            WHERE account_id = %s
              AND scored_at > NOW() - INTERVAL '%s minutes'""",
        (payment["debtor_profile_id"], settings.VELOCITY_WINDOW_MINUTES),
        fetch="one",
    )
    if row and row["c"] >= settings.VELOCITY_MAX_PAYMENTS:
        return 30, f"{row['c']} payments in the last {settings.VELOCITY_WINDOW_MINUTES} minutes"
    return None


def deviation_from_baseline(payment):
    row = query(
        "SELECT avg_amount_minor FROM account_baselines WHERE account_id = %s",
        (payment["debtor_profile_id"],), fetch="one",
    )
    if not row or not row["avg_amount_minor"]:
        return None
    if payment["amount_minor"] > row["avg_amount_minor"] * 10:
        return 35, "amount more than ten times the account average"
    return None


RULES = [high_value, unusual_hour, velocity, deviation_from_baseline]


def score_payment(payment):
    total = 0
    hits = []
    for rule in RULES:
        result = rule(payment)
        if result:
            points, reason = result
            total += points
            hits.append({"rule": rule.__name__, "points": points, "reason": reason})
    return min(total, 100), hits
