# TrolleyWise Payment Integration & Sandbox Setup

## 1. Supported Payment Rails
- **UPI Deep-Linking & Dynamic QR:** Standard NPCI URI specification (`upi://pay?pa=...&tr=...&am=...`).
- **Payment Gateway Sandbox:** Razorpay / Cashfree sandbox compatibility.
- **Card & NetBanking:** Supported via Gateway Order API.

---

## 2. Server-Side Signature Verification & Idempotency
TrolleyWise **never** marks a transaction as paid based on a frontend client response. Payment completion requires authentic cryptographic proof:

```python
# Server computes HMAC-SHA256 signature
expected_signature = hmac.new(
    PAYMENT_KEY_SECRET.encode('utf-8'),
    f"{order_id}|{payment_id}".encode('utf-8'),
    hashlib.sha256
).hexdigest()

assert hmac.compare_digest(expected_signature, received_signature)
```

### Idempotency Protection:
- Every payment attempt carries an `idempotency_key`.
- Repeated payment attempts or duplicate webhook callbacks for the same transaction ID are handled safely without duplicate inventory deductions or double billing.

---

## 3. Configuration Variables

In `.env`:
```ini
PAYMENT_PROVIDER="RAZORPAY_SANDBOX"
PAYMENT_KEY_ID="rzp_test_trolleywise_sandbox_key"
PAYMENT_KEY_SECRET="tw_secret_sandbox_signature_9921"
PAYMENT_WEBHOOK_SECRET="tw_whsec_secret_2026"
UPI_VPA="trolleywise@icici"
```
