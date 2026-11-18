from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.db.models import VerificationEvent, AnomalyEvent
from backend.app.schemas.verification import VerificationEvaluateRequest, AnomalyResolveRequest
from backend.app.services.sensor_fusion import sensor_fusion_engine
from backend.app.services.anomaly_detector import anomaly_detector
from backend.app.services.billing_engine import billing_engine
from backend.app.services.websocket_manager import ws_manager

router = APIRouter()

@router.post("/evaluate")
async def evaluate_multimodal_event(
    req: VerificationEvaluateRequest,
    db: Session = Depends(get_db)
):
    """
    Core Patent Verification Pipeline:
    Ingests visual candidate event + pre/post sensor telemetry.
    Applies multimodal fusion.
    Only VERIFIED events modify the confirmed digital cart!
    """
    eval_result = sensor_fusion_engine.evaluate_event(
        db=db,
        session_id=req.session_id,
        visual_event=req.visual_event,
        sensor_reading_pre=req.sensor_reading_pre,
        sensor_reading_post=req.sensor_reading_post
    )

    event_type = eval_result.get("event_type")
    product_id = eval_result.get("product_id")
    ver_event_id = eval_result.get("verification_event_id")

    bill_update = None
    if event_type == "VERIFIED_INSERTION" and product_id:
        bill_update = billing_engine.add_verified_product(
            db=db,
            session_id=req.session_id,
            product_id=product_id,
            verified_event_id=ver_event_id
        )
    elif event_type == "VERIFIED_REMOVAL" and product_id:
        bill_update = billing_engine.remove_verified_product(
            db=db,
            session_id=req.session_id,
            product_id=product_id,
            verified_event_id=ver_event_id
        )

    # Broadcast live status update to Customer Touchscreen via WebSocket
    ws_payload = {
        "type": "VERIFICATION_UPDATE",
        "eval_result": eval_result,
        "bill_update": bill_update
    }
    await ws_manager.broadcast_to_channel(str(req.session_id), ws_payload)
    await ws_manager.broadcast_to_channel("retailer", ws_payload)

    return {
        "evaluation": eval_result,
        "cart_updated": event_type in ["VERIFIED_INSERTION", "VERIFIED_REMOVAL"],
        "bill": bill_update
    }

@router.get("/events")
def get_verification_events(
    session_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(VerificationEvent)
    if session_id:
        query = query.filter(VerificationEvent.session_id == session_id)
    events = query.order_by(VerificationEvent.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": e.id,
            "session_id": e.session_id,
            "event_type": e.event_type,
            "product_name": e.product.name if e.product else None,
            "sku": e.product.sku if e.product else None,
            "observed_weight_delta": e.observed_weight_delta,
            "expected_weight": e.expected_weight,
            "overall_confidence": e.overall_confidence,
            "status": e.status,
            "created_at": e.created_at.isoformat() if e.created_at else None
        }
        for e in events
    ]

@router.get("/anomalies")
def get_anomalies(
    session_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    return anomaly_detector.list_unresolved_anomalies(db, session_id)

@router.post("/anomalies/{anomaly_id}/resolve")
async def resolve_anomaly(
    anomaly_id: int,
    req: AnomalyResolveRequest,
    db: Session = Depends(get_db)
):
    resolved = anomaly_detector.resolve_anomaly(
        db=db,
        anomaly_id=anomaly_id,
        resolution_action=req.resolution_action,
        resolved_by=req.resolved_by,
        resolution_notes=req.resolution_notes
    )

    # Broadcast resolution to screen
    await ws_manager.broadcast_to_channel(
        str(resolved["session_id"]),
        {"type": "ANOMALY_RESOLVED", "anomaly": resolved}
    )

    return resolved
