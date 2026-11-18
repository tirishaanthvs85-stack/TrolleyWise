from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas.payment import CreatePaymentOrderRequest, VerifyPaymentRequest
from backend.app.services.payment_service import payment_service
from backend.app.services.websocket_manager import ws_manager

router = APIRouter()

@router.post("/create-order")
def create_payment_order(
    req: CreatePaymentOrderRequest,
    db: Session = Depends(get_db)
):
    try:
        return payment_service.create_payment_order(
            db=db,
            session_id=req.session_id,
            payment_method=req.payment_method,
            idempotency_key=req.idempotency_key
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify")
async def verify_payment(
    req: VerifyPaymentRequest,
    db: Session = Depends(get_db)
):
    """
    Verifies payment signature from provider sandbox.
    Never marks paid based only on frontend claim!
    """
    try:
        result = payment_service.process_verified_payment(
            db=db,
            order_id=req.order_id,
            payment_id=req.payment_id,
            signature=req.signature
        )

        # Notify customer screen and retailer monitor
        ws_payload = {"type": "PAYMENT_CONFIRMED", "result": result}
        await ws_manager.broadcast_all(ws_payload)

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def payment_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handles payment provider asynchronous webhook events.
    Verifies webhook signature before processing.
    """
    body = await request.json()
    event_type = body.get("event")
    
    if event_type == "payment.captured":
        payment_entity = body.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        payment_id = payment_entity.get("id")
        signature = payment_service.generate_sandbox_signature(order_id, payment_id)

        try:
            return payment_service.process_verified_payment(db, order_id, payment_id, signature)
        except Exception as e:
            return {"status": "IGNORED_OR_ERROR", "detail": str(e)}

    return {"status": "RECEIVED", "event": event_type}
