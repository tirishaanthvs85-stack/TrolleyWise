import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.db.models import ShoppingSession, TrolleyDevice, Customer, Store, DigitalCart
from backend.app.schemas.session import SessionCreate, SessionOut, SessionEventCreate
from backend.app.services.billing_engine import billing_engine

router = APIRouter()

@router.post("", response_model=SessionOut)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)):
    trolley = db.query(TrolleyDevice).filter(TrolleyDevice.device_uuid == payload.trolley_uuid).first()
    if not trolley:
        raise HTTPException(status_code=404, detail="Trolley not found")

    store = db.query(Store).filter(Store.store_code == payload.store_code).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    token = f"TW-SESS-{uuid.uuid4().hex[:12].upper()}"
    new_session = ShoppingSession(
        session_token=token,
        trolley_id=trolley.id,
        customer_id=payload.customer_id,
        store_id=store.id,
        budget_limit=payload.budget_limit,
        status="ACTIVE"
    )
    db.add(new_session)
    db.flush()

    # Initialize Digital Cart
    cart = DigitalCart(session_id=new_session.id, version=1, total_weight_grams=0.0, status="ACTIVE")
    db.add(cart)

    trolley.status = "SHOPPING"
    db.commit()
    db.refresh(new_session)

    cust_name = new_session.customer.full_name if new_session.customer else "Guest Customer"

    return SessionOut(
        id=new_session.id,
        session_token=new_session.session_token,
        trolley_uuid=trolley.device_uuid,
        customer_name=cust_name,
        store_code=store.store_code,
        status=new_session.status,
        budget_limit=new_session.budget_limit,
        started_at=new_session.started_at.isoformat()
    )

@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    cust_name = session.customer.full_name if session.customer else "Guest Customer"
    return SessionOut(
        id=session.id,
        session_token=session.session_token,
        trolley_uuid=session.trolley.device_uuid,
        customer_name=cust_name,
        store_code=session.store.store_code,
        status=session.status,
        budget_limit=session.budget_limit,
        started_at=session.started_at.isoformat()
    )

@router.get("/{session_id}/cart")
def get_session_cart(session_id: int, db: Session = Depends(get_db)):
    bill_data = billing_engine.recalculate_bill(db, session_id)
    return bill_data

@router.post("/{session_id}/events")
def post_session_event(session_id: int, event: SessionEventCreate, db: Session = Depends(get_db)):
    session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "status": "EVENT_RECORDED",
        "session_id": session_id,
        "event_type": event.event_type,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
