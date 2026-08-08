from pydantic import BaseModel, Field
from typing import Optional


class PaymentRequest(BaseModel):
    debtor_profile_id: str
    creditor_sort_code: str = Field(..., pattern=r"^\d{2}-\d{2}-\d{2}$")
    creditor_account_number: str = Field(..., min_length=8, max_length=8)
    creditor_name: str
    amount_minor: int = Field(..., gt=0, description="Amount in pence")
    currency: str = "GBP"
    reference: Optional[str] = None
    idempotency_key: str


class PaymentResponse(BaseModel):
    id: str
    state: str
    amount_minor: int
    currency: str
    partner_reference: Optional[str] = None
    created_at: Optional[str] = None
