from typing import Optional
from decimal import Decimal
from pydantic import BaseModel

class CreatePaymentOrderRequest(BaseModel):
    session_id: int
    payment_method: str = "UPI"
    idempotency_key: Optional[str] = None

class VerifyPaymentRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str

class PaymentWebhookPayload(BaseModel):
    event: str
    payload: dict
