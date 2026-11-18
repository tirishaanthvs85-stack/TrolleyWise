from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas.billing import RecalculateBillRequest, CheckoutRequest
from backend.app.services.billing_engine import billing_engine
from backend.app.services.payment_service import payment_service
from backend.app.services.websocket_manager import ws_manager

router = APIRouter()

@router.get("/{session_id}")
def get_current_bill(session_id: int, db: Session = Depends(get_db)):
    try:
        bill = billing_engine.recalculate_bill(db, session_id)
        return bill
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{session_id}/recalculate")
async def recalculate_bill(
    session_id: int,
    req: RecalculateBillRequest,
    db: Session = Depends(get_db)
):
    try:
        bill = billing_engine.recalculate_bill(db, session_id, coupon_code=req.coupon_code)
        await ws_manager.broadcast_to_channel(str(session_id), {"type": "BILL_UPDATED", "bill": bill})
        return bill
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{session_id}/checkout")
async def initiate_checkout(
    session_id: int,
    req: CheckoutRequest,
    db: Session = Depends(get_db)
):
    """
    Freezes cart version, validates zero unresolved anomalies,
    creates payment order, and returns dynamic UPI QR payment info.
    """
    try:
        # 1. Freeze cart
        tx = billing_engine.freeze_cart_for_checkout(db, session_id)

        # 2. Create authorized payment order
        order_info = payment_service.create_payment_order(
            db=db,
            session_id=session_id,
            payment_method=req.payment_method,
            idempotency_key=req.idempotency_key
        )

        await ws_manager.broadcast_to_channel(
            str(session_id),
            {"type": "CHECKOUT_INITIATED", "order": order_info}
        )

        return order_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
