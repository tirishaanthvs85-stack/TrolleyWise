"""
TrolleyWise Anomaly Detection & Resolution Engine
Adheres to Section 5:
- Independent detection of physical vs digital mismatches
- Auditable anomaly logging with severity levels (LOW, MEDIUM, HIGH, CRITICAL)
- Guided resolution workflow (Pause -> Reprocess -> Customer Confirm -> Staff Assist)
- Resolution status tracking (DETECTED, INVESTIGATING, RESOLVED, DISMISSED)
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.db.models import AnomalyEvent, ShoppingSession, DigitalCart, CartItem, ProductCatalog

class AnomalyDetectionEngine:
    def list_unresolved_anomalies(self, db: Session, session_id: Optional[int] = None) -> List[AnomalyEvent]:
        """Returns all currently active / unresolved anomalies."""
        query = db.query(AnomalyEvent).filter(AnomalyEvent.status.in_(["DETECTED", "INVESTIGATING"]))
        if session_id:
            query = query.filter(AnomalyEvent.session_id == session_id)
        return query.order_by(AnomalyEvent.detected_at.desc()).all()

    def check_physical_digital_mismatch(
        self,
        db: Session,
        session_id: int,
        physical_weight_grams: float
    ) -> Optional[AnomalyEvent]:
        """
        Periodically audits the cumulative physical weight measured by the load cells
        against the sum of expected weights of all items currently in the digital cart.
        """
        session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
        if not session or not session.cart:
            return None

        # Calculate expected digital cart weight
        expected_total_weight = 0.0
        for item in session.cart.items:
            prod_weight = item.product.weight_record.expected_weight_grams if item.product.weight_record else 0.0
            expected_total_weight += (prod_weight * item.quantity)

        discrepancy = abs(physical_weight_grams - expected_total_weight)
        
        # Tolerance margin for cumulative shopping cart: 40 grams
        if discrepancy > 40.0:
            anomaly = AnomalyEvent(
                session_id=session_id,
                anomaly_type="PHYSICAL_DIGITAL_CART_MISMATCH",
                description=(
                    f"Cumulative basket weight mismatch: Measured physical weight is {physical_weight_grams:.1f}g, "
                    f"but expected digital cart weight is {expected_total_weight:.1f}g (Δ: {discrepancy:+.1f}g)."
                ),
                severity="HIGH" if discrepancy > 150.0 else "MEDIUM",
                status="DETECTED"
            )
            db.add(anomaly)
            db.commit()
            db.refresh(anomaly)
            return anomaly

        return None

    def resolve_anomaly(
        self,
        db: Session,
        anomaly_id: int,
        resolution_action: str, # "CUSTOMER_CONFIRMED", "STAFF_OVERRIDE", "DISMISSED", "CORRECTED"
        resolved_by: str,
        resolution_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes patent anomaly resolution workflow:
        Updates anomaly status, stores audit record, and allows the billing transition to resume.
        """
        anomaly = db.query(AnomalyEvent).filter(AnomalyEvent.id == anomaly_id).first()
        if not anomaly:
            raise ValueError(f"Anomaly ID {anomaly_id} not found.")

        now = datetime.now(timezone.utc)
        anomaly.status = "RESOLVED" if resolution_action != "DISMISSED" else "DISMISSED"
        anomaly.resolved_by = resolved_by
        anomaly.resolution_notes = f"Action: {resolution_action}. Details: {resolution_notes or 'Resolved successfully.'}"
        anomaly.resolved_at = now

        db.commit()
        db.refresh(anomaly)

        return {
            "anomaly_id": anomaly.id,
            "session_id": anomaly.session_id,
            "anomaly_type": anomaly.anomaly_type,
            "status": anomaly.status,
            "resolved_by": anomaly.resolved_by,
            "resolved_at": anomaly.resolved_at.isoformat(),
            "notes": anomaly.resolution_notes
        }

# Global singleton
anomaly_detector = AnomalyDetectionEngine()
