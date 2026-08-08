"""Client for the BaaS partner bank.

Meridian holds no banking licence. Customer funds sit in a pooled safeguarding
account at the partner bank, and this is the only path by which money physically
leaves the platform.
"""
import logging

import httpx

from app.config import settings

log = logging.getLogger(__name__)


class PartnerBankError(Exception):
    """Raised when the partner bank is unreachable or rejects the instruction."""


def submit_payment(payment_id: str, sort_code: str, account_number: str,
                   creditor_name: str, amount_minor: int, currency: str):
    payload = {
        "instruction_id": payment_id,
        "creditor": {
            "sort_code": sort_code,
            "account_number": account_number,
            "name": creditor_name,
        },
        "amount": {"minor_units": amount_minor, "currency": currency},
    }
    try:
        with httpx.Client(timeout=settings.PARTNER_BANK_TIMEOUT) as client:
            resp = client.post(
                f"{settings.PARTNER_BANK_URL}/v1/payments",
                headers={"Authorization": f"Bearer {settings.PARTNER_BANK_API_KEY}"},
                json=payload,
            )
    except httpx.RequestError as exc:
        raise PartnerBankError(f"partner bank unreachable: {exc}") from exc

    if resp.status_code >= 500:
        raise PartnerBankError(f"partner bank error {resp.status_code}")
    if resp.status_code >= 400:
        raise PartnerBankError(f"instruction rejected: {resp.text}")

    return resp.json()
