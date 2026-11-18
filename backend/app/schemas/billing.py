from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel

class RecalculateBillRequest(BaseModel):
    coupon_code: Optional[str] = None

class CheckoutRequest(BaseModel):
    payment_method: str = "UPI"
    idempotency_key: Optional[str] = None
