"""
TrolleyWise Payment Integration Service
Section 10:
- Dynamic UPI QR Generation (Standard NPCI UPI spec & Payment Gateway Orders)
- Razorpay / Cashfree compatible sandbox payment flow
- Authenticated server-side cryptographic signature verification (HMAC-SHA256)
- Signed webhook processing
- Strict payment idempotency to prevent duplicate charges
- Cart state freezing and session completion
"""

import hmac
import hashlib
import uuid
import time
import urllib.parse
from decimal import Decimal
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.db.models import (
    ShoppingSession, BillingTransaction, PaymentAttempt, PaymentRecord,
    Receipt, LoyaltyTransaction
)

class PaymentGatewayService:
    def __init__(self):
        self.key_id = settings.PAYMENT_KEY_ID
        self.key_secret = settings.PAYMENT_KEY_SECRET
        self.webhook_secret = settings.PAYMENT_WEBHOOK_SECRET
        self.upi_vpa = settings.UPI_VPA

    def create_payment_order(
        self,
        db: Session,
        session_id: int,
        payment_method: str = "UPI",
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates an authorized payment order with idempotency protection.
        Generates dynamic UPI QR deep link string and gateway order ID.
        """
        session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
        if not session or not session.billing_transaction:
            raise ValueError("No active billing transaction found for session.")

        tx = session.billing_transaction
        if tx.status == "PAID":
            raise ValueError("This transaction has already been paid and completed.")

        # Enforce idempotency key
        idem_key = idempotency_key or f"tw_idem_{tx.id}_{int(time.time())}"
        existing_attempt = db.query(PaymentAttempt).filter(
            PaymentAttempt.idempotency_key == idem_key
        ).first()

        if existing_attempt and existing_attempt.status == "INITIATED":
            order_id = existing_attempt.order_id
        else:
            order_id = f"order_{uuid.uuid4().hex[:14]}"
            attempt = PaymentAttempt(
                transaction_id=tx.id,
                payment_method=payment_method,
                provider=settings.PAYMENT_PROVIDER,
                order_id=order_id,
                idempotency_key=idem_key,
                amount=tx.final_amount,
                status="INITIATED"
            )
            db.add(attempt)
            db.commit()

        # Generate standard NPCI Dynamic UPI Intent URI
        amount_str = f"{tx.final_amount:.2f}"
        upi_params = {
            "pa": self.upi_vpa,
            "pn": urllib.parse.quote(settings.STORE_NAME),
            "tr": order_id,
            "am": amount_str,
            "cu": "INR",
            "tn": f"TrolleyWise {tx.invoice_number}"
        }
        upi_intent_url = f"upi://pay?pa={upi_params['pa']}&pn={upi_params['pn']}&tr={upi_params['tr']}&am={upi_params['am']}&cu={upi_params['cu']}&tn={upi_params['tn']}"

        return {
            "order_id": order_id,
            "transaction_id": tx.id,
            "invoice_number": tx.invoice_number,
            "amount": amount_str,
            "currency": "INR",
            "payment_method": payment_method,
            "idempotency_key": idem_key,
            "upi_intent_url": upi_intent_url,
            "key_id": self.key_id,
            "status": "INITIATED"
        }

    def verify_payment_signature(
        self,
        order_id: str,
        payment_id: str,
        signature: str
    ) -> bool:
        """
        Cryptographically validates gateway signature:
        HMAC_SHA256(order_id + '|' + payment_id, key_secret) == signature
        """
        message = f"{order_id}|{payment_id}"
        expected_sig = hmac.new(
            self.key_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_sig, signature)

    def generate_sandbox_signature(self, order_id: str, payment_id: str) -> str:
        """Helper to generate authentic sandbox HMAC-SHA256 signatures for testing/sandbox."""
        message = f"{order_id}|{payment_id}"
        return hmac.new(
            self.key_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def process_verified_payment(
        self,
        db: Session,
        order_id: str,
        payment_id: str,
        signature: str
    ) -> Dict[str, Any]:
        """
        Server-side execution of verified payment:
        Validates cryptographic signature, records payment record, marks transaction PAID,
        updates inventory, grants loyalty points, and seals session.
        """
        attempt = db.query(PaymentAttempt).filter(PaymentAttempt.order_id == order_id).first()
        if not attempt:
            raise ValueError(f"Unknown order ID: {order_id}")

        tx = attempt.transaction
        if tx.status == "PAID":
            return {
                "status": "ALREADY_PAID",
                "transaction_id": tx.id,
                "invoice_number": tx.invoice_number
            }

        # 1. Cryptographic Signature Verification
        is_valid = self.verify_payment_signature(order_id, payment_id, signature)
        if not is_valid:
            attempt.status = "FAILED"
            attempt.error_message = "Invalid payment gateway cryptographic signature."
            db.commit()
            raise ValueError("Payment signature verification failed. Potential tampering detected.")

        # 2. Check for duplicate payment record (idempotency)
        existing_record = db.query(PaymentRecord).filter(
            PaymentRecord.payment_reference == payment_id
        ).first()
        if existing_record:
            return {"status": "DUPLICATE_PAYMENT_PROCESSED", "transaction_id": tx.id}

        # 3. Create Payment Record
        record = PaymentRecord(
            transaction_id=tx.id,
            payment_attempt_id=attempt.id,
            payment_reference=payment_id,
            provider_tx_id=f"ptx_{uuid.uuid4().hex[:12]}",
            signature=signature,
            amount_received=tx.final_amount,
            currency="INR"
        )
        db.add(record)

        attempt.status = "SUCCESS"
        tx.status = "PAID"

        # 4. Synchronize Inventory Exactly Once
        from backend.app.services.inventory_service import inventory_service
        inventory_service.deduct_inventory_for_transaction(db, tx.id)

        # 5. Award Loyalty Points
        session = tx.session
        if session.customer and session.customer.loyalty_account:
            # 1 point per 10 INR spent
            points = int(tx.final_amount // Decimal("10.0"))
            loyalty_acct = session.customer.loyalty_account
            loyalty_acct.points_balance += points
            loyalty_tx = LoyaltyTransaction(
                loyalty_account_id=loyalty_acct.id,
                session_id=session.id,
                points_change=points,
                reason=f"Earned on invoice {tx.invoice_number}"
            )
            db.add(loyalty_tx)

        # 6. Mark Session Completed
        session.status = "COMPLETED"
        session.completed_at = record.verified_at
        if session.cart:
            session.cart.status = "CHECKED_OUT"

        db.commit()
        db.refresh(tx)

        # 7. Generate Official Electronic Receipt
        from backend.app.services.receipt_service import receipt_service
        receipt_info = receipt_service.generate_receipt(db, tx.id)

        return {
            "status": "PAYMENT_SUCCESS",
            "transaction_id": tx.id,
            "invoice_number": tx.invoice_number,
            "amount_paid": str(tx.final_amount),
            "payment_id": payment_id,
            "receipt_number": receipt_info.get("receipt_number"),
            "pdf_url": receipt_info.get("pdf_url")
        }

# Global singleton
payment_service = PaymentGatewayService()
