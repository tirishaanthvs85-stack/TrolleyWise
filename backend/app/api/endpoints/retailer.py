from decimal import Decimal
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.db.models import (
    BillingTransaction, TrolleyDevice, AnomalyEvent, Inventory, 
    ProductCatalog, ShoppingSession, Promotion
)

router = APIRouter()

@router.get("/dashboard-stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Summary KPI metrics for retailer executive console."""
    completed_txs = db.query(BillingTransaction).filter(BillingTransaction.status == "PAID").all()
    total_revenue = sum((tx.final_amount for tx in completed_txs), Decimal("0.00"))
    
    active_sessions = db.query(ShoppingSession).filter(ShoppingSession.status == "ACTIVE").count()
    active_trolleys = db.query(TrolleyDevice).filter(TrolleyDevice.status != "OFFLINE").count()
    unresolved_anomalies = db.query(AnomalyEvent).filter(AnomalyEvent.status.in_(["DETECTED", "INVESTIGATING"])).count()
    low_stock_items = db.query(Inventory).filter(Inventory.current_stock <= Inventory.min_threshold).count()

    return {
        "total_revenue": str(total_revenue),
        "completed_transactions_count": len(completed_txs),
        "active_shopping_sessions": active_sessions,
        "active_trolleys_count": active_trolleys,
        "unresolved_anomalies_count": unresolved_anomalies,
        "low_stock_alerts_count": low_stock_items
    }

@router.get("/transactions")
def get_transactions(limit: int = 20, db: Session = Depends(get_db)):
    txs = db.query(BillingTransaction).order_by(BillingTransaction.created_at.desc()).limit(limit).all()
    return [
        {
            "id": tx.id,
            "invoice_number": tx.invoice_number,
            "session_id": tx.session_id,
            "trolley": tx.session.trolley.device_uuid if tx.session and tx.session.trolley else "N/A",
            "customer": tx.session.customer.full_name if tx.session and tx.session.customer else "Guest",
            "final_amount": str(tx.final_amount),
            "status": tx.status,
            "created_at": tx.created_at.isoformat() if tx.created_at else None
        }
        for tx in txs
    ]

@router.get("/trolleys")
def get_trolleys(db: Session = Depends(get_db)):
    trolleys = db.query(TrolleyDevice).all()
    return [
        {
            "id": t.id,
            "device_uuid": t.device_uuid,
            "status": t.status,
            "battery_level": t.battery_level,
            "firmware_version": t.firmware_version,
            "ip_address": t.ip_address,
            "last_heartbeat": t.last_heartbeat.isoformat() if t.last_heartbeat else None
        }
        for t in trolleys
    ]
