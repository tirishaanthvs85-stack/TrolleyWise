"""
TrolleyWise Multimodal Product Verification Engine
Central Patent Mechanism (Section 4):
Multimodal Sensor Fusion Pipeline:
Visual AI (35%) + Weight Consistency (30%) + Temporal Alignment (15%) +
Tracking Continuity (10%) + Motion Stability (5%) + Cart-State Consistency (5%)

Evaluates Physical Movement vs Digital State into 4 states:
- VERIFIED_INSERTION
- VERIFIED_REMOVAL
- UNCERTAIN_EVENT
- ANOMALY_EVENT

Only verified events modify the confirmed billing cart.
"""

import time
import math
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.db.models import (
    ShoppingSession, DigitalCart, CartItem, ProductCatalog, 
    ProductWeight, VerificationEvent, AnomalyEvent
)

class MultimodalVerificationEngine:
    def __init__(self):
        self.w_visual = settings.WEIGHT_SCORE_VISUAL
        self.w_weight = settings.WEIGHT_SCORE_WEIGHT
        self.w_temporal = settings.WEIGHT_SCORE_TEMPORAL
        self.w_tracking = settings.WEIGHT_SCORE_TRACKING
        self.w_motion = settings.WEIGHT_SCORE_MOTION
        self.w_cart_state = settings.WEIGHT_SCORE_CART_STATE
        self.conf_threshold = settings.VERIFICATION_CONFIDENCE_THRESHOLD
        self.uncertainty_threshold = settings.UNCERTAINTY_THRESHOLD

    def evaluate_event(
        self,
        db: Session,
        session_id: int,
        visual_event: Optional[Dict[str, Any]],
        sensor_reading_pre: Dict[str, Any],
        sensor_reading_post: Dict[str, Any],
        event_timestamp: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes patent multimodal sensor fusion algorithm.
        Correlates RGB camera visual recognition, load cell weight transitions,
        IMU motion status, temporal alignment, and digital cart state.
        """
        now = event_timestamp or time.time()
        
        # 1. Fetch Session and Cart
        shopping_session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
        if not shopping_session:
            raise ValueError(f"Invalid shopping session ID: {session_id}")

        cart = shopping_session.cart
        if not cart:
            raise ValueError(f"Digital cart not initialized for session: {session_id}")

        # 2. Extract Weight & IMU measurements
        w_pre = float(sensor_reading_pre.get("filtered_weight_grams", sensor_reading_pre.get("raw_weight_grams", 0.0)))
        w_post = float(sensor_reading_post.get("filtered_weight_grams", sensor_reading_post.get("raw_weight_grams", 0.0)))
        observed_delta_w = round(w_post - w_pre, 2)
        
        imu_post = sensor_reading_post.get("imu", {})
        is_moving = sensor_reading_post.get("is_moving", imu_post.get("is_moving", False))
        is_stable = sensor_reading_post.get("is_stable", not is_moving)

        # 3. Check Motion Stability Score
        if is_moving or not is_stable:
            score_motion = 0.0
        else:
            score_motion = 1.0

        # If cart is actively in motion, do NOT finalize weight-based events
        if is_moving:
            anomaly_desc = "Trolley in motion during weight acquisition. Event deferred for stability."
            return self._record_and_return_anomaly(
                db, session_id, "MOTION_INSTABILITY_DEFERRAL", anomaly_desc,
                observed_delta_w, 0.0, "MEDIUM", is_deferred=True
            )

        # 4. Scenario A: Weight change detected with NO visual detection
        if not visual_event or not visual_event.get("sku"):
            if abs(observed_delta_w) >= settings.WEIGHT_TOLERANCE_MIN_GRAMS:
                anomaly_desc = (
                    f"Weight transition of {observed_delta_w:+.1f}g detected without corresponding visual product recognition. "
                    f"Possible blind-spot placement or unregistered item."
                )
                return self._record_and_return_anomaly(
                    db, session_id, "UNRECOGNIZED_WEIGHT_CHANGE", anomaly_desc,
                    observed_delta_w, 0.0, "HIGH"
                )
            else:
                # Negligible drift within noise floor
                return {
                    "event_type": "NO_EVENT",
                    "status": "IDLE",
                    "confidence": 1.0,
                    "description": "Baseline weight stable. No product activity."
                }

        # 5. Look up Product in Catalogue
        sku = visual_event["sku"]
        product = db.query(ProductCatalog).filter(ProductCatalog.sku == sku, ProductCatalog.is_active == True).first()
        if not product:
            anomaly_desc = f"Visual detection produced unrecognized catalogue SKU: {sku}"
            return self._record_and_return_anomaly(
                db, session_id, "UNKNOWN_CATALOGUE_SKU", anomaly_desc,
                observed_delta_w, 0.0, "HIGH"
            )

        expected_w = float(product.weight_record.expected_weight_grams) if product.weight_record else 100.0
        tolerance_w = float(product.weight_record.weight_tolerance_grams) if product.weight_record else settings.WEIGHT_TOLERANCE_MIN_GRAMS
        
        direction = visual_event.get("direction", "INWARD").upper()
        
        # 6. Evaluate Individual Modality Scores
        # 6a. Visual Confidence Score
        score_visual = min(1.0, max(0.0, float(visual_event.get("confidence", 0.0))))

        # 6b. Weight Consistency Score
        if direction == "INWARD":
            target_delta = expected_w
        else: # OUTWARD / REMOVAL
            target_delta = -expected_w

        weight_err = abs(observed_delta_w - target_delta)
        if weight_err <= tolerance_w:
            score_weight = 1.0 - (weight_err / (tolerance_w * 2.0))
        elif weight_err <= (tolerance_w * 2.5):
            score_weight = max(0.1, 1.0 - (weight_err / (tolerance_w * 3.0)))
        else:
            score_weight = 0.0

        # If weight discrepancy is severe, flag as explicit ANOMALY_EVENT
        if score_weight == 0.0:
            anomaly_desc = (
                f"Severe weight mismatch for '{product.name}' ({sku}). Expected {target_delta:+.1f}g (±{tolerance_w}g), "
                f"but load cells measured {observed_delta_w:+.1f}g (Discrepancy: {weight_err:+.1f}g). "
                f"Possible multiple products entered together or substituted item."
            )
            return self._record_and_return_anomaly(
                db, session_id, "WEIGHT_MISMATCH_ANOMALY", anomaly_desc,
                observed_delta_w, target_delta, "HIGH", product_id=product.id
            )

        # 6c. Temporal Alignment Score
        vision_timestamp = visual_event.get("timestamp", now)
        time_diff = abs(now - vision_timestamp)
        if time_diff <= 1.5:
            score_temporal = 1.0
        elif time_diff <= 4.0:
            score_temporal = max(0.2, 1.0 - ((time_diff - 1.5) / 2.5))
        else:
            score_temporal = 0.1

        # 6d. Tracking Continuity Score
        frames_tracked = visual_event.get("frames_tracked", 2)
        if frames_tracked >= 3:
            score_tracking = 1.0
        elif frames_tracked == 2:
            score_tracking = 0.8
        else:
            score_tracking = 0.5

        # 6e. Cart State Consistency Score
        existing_cart_item = db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product.id
        ).first()

        if direction == "OUTWARD":
            # For removal, item MUST exist in confirmed cart
            if existing_cart_item and existing_cart_item.quantity > 0:
                score_cart_state = 1.0
            else:
                # Customer removing an item that was never registered in digital cart
                score_cart_state = 0.0
        else: # INWARD
            score_cart_state = 1.0

        # 7. Compute Multimodal Sensor Fusion Overall Confidence
        overall_confidence = (
            (score_visual * self.w_visual) +
            (score_weight * self.w_weight) +
            (score_temporal * self.w_temporal) +
            (score_tracking * self.w_tracking) +
            (score_motion * self.w_motion) +
            (score_cart_state * self.w_cart_state)
        )
        overall_confidence = round(min(1.0, max(0.0, overall_confidence)), 4)

        # 8. Check for Weight Anomaly (visual detection with no weight change or inverse weight change)
        if direction == "INWARD" and observed_delta_w <= settings.WEIGHT_TOLERANCE_MIN_GRAMS:
            anomaly_desc = (
                f"Product '{product.name}' visually detected entering cart, but no stable positive weight "
                f"was recorded (observed ΔW: {observed_delta_w:+.1f}g, expected: +{expected_w}g)."
            )
            return self._record_and_return_anomaly(
                db, session_id, "VISUAL_WITHOUT_WEIGHT_CHANGE", anomaly_desc,
                observed_delta_w, expected_w, "MEDIUM", product_id=product.id
            )

        if direction == "OUTWARD" and observed_delta_w >= -settings.WEIGHT_TOLERANCE_MIN_GRAMS:
            anomaly_desc = (
                f"Product '{product.name}' visually detected leaving cart, but no negative weight reduction "
                f"was recorded (observed ΔW: {observed_delta_w:+.1f}g, expected: -{expected_w}g)."
            )
            return self._record_and_return_anomaly(
                db, session_id, "REMOVAL_WITHOUT_WEIGHT_DROP", anomaly_desc,
                observed_delta_w, -expected_w, "MEDIUM", product_id=product.id
            )

        if direction == "OUTWARD" and (not existing_cart_item or existing_cart_item.quantity <= 0):
            anomaly_desc = (
                f"Removal detected for '{product.name}' ({sku}), but product is not present in confirmed cart."
            )
            return self._record_and_return_anomaly(
                db, session_id, "UNREGISTERED_PRODUCT_REMOVAL", anomaly_desc,
                observed_delta_w, -expected_w, "HIGH", product_id=product.id
            )

        # 9. Determine Event State based on Confidence & Modality Gates
        # Both overall confidence and minimum visual clarity (>= 0.60) are required for automatic verification
        if overall_confidence >= self.conf_threshold and score_visual >= 0.60:
            event_type = "VERIFIED_INSERTION" if direction == "INWARD" else "VERIFIED_REMOVAL"
            event_status = "CONFIRMED"
        elif overall_confidence >= self.uncertainty_threshold:
            event_type = "UNCERTAIN_EVENT"
            event_status = "PENDING_CONFIRMATION"
        else:
            anomaly_desc = (
                f"Low multimodal confidence ({overall_confidence:.2f}) for '{product.name}'. "
                f"Visual={score_visual:.2f}, Weight={score_weight:.2f}, Motion={score_motion:.2f}"
            )
            return self._record_and_return_anomaly(
                db, session_id, "LOW_CONFIDENCE_MULTIMODAL_MISMATCH", anomaly_desc,
                observed_delta_w, target_delta, "MEDIUM", product_id=product.id
            )

        # 10. Persist Verification Event
        ver_event = VerificationEvent(
            session_id=session_id,
            event_type=event_type,
            product_id=product.id,
            observed_weight_delta=observed_delta_w,
            expected_weight=target_delta,
            score_visual=score_visual,
            score_weight=score_weight,
            score_temporal=score_temporal,
            score_tracking=score_tracking,
            score_motion=score_motion,
            score_cart_state=score_cart_state,
            overall_confidence=overall_confidence,
            status=event_status
        )
        db.add(ver_event)
        db.commit()
        db.refresh(ver_event)

        return {
            "verification_event_id": ver_event.id,
            "event_type": event_type,
            "product_id": product.id,
            "sku": product.sku,
            "product_name": product.name,
            "observed_weight_delta": observed_delta_w,
            "expected_weight": target_delta,
            "overall_confidence": overall_confidence,
            "scores": {
                "visual": score_visual,
                "weight": score_weight,
                "temporal": score_temporal,
                "tracking": score_tracking,
                "motion": score_motion,
                "cart_state": score_cart_state
            },
            "status": event_status,
            "direction": direction
        }

    def _record_and_return_anomaly(
        self,
        db: Session,
        session_id: int,
        anomaly_type: str,
        description: str,
        observed_delta: float,
        expected_delta: float,
        severity: str = "MEDIUM",
        product_id: Optional[int] = None,
        is_deferred: bool = False
    ) -> Dict[str, Any]:
        """Creates an auditable anomaly record and verification event."""
        ver_event = VerificationEvent(
            session_id=session_id,
            event_type="ANOMALY_EVENT",
            product_id=product_id,
            observed_weight_delta=observed_delta,
            expected_weight=expected_delta,
            score_visual=0.0,
            score_weight=0.0,
            score_temporal=0.0,
            score_tracking=0.0,
            score_motion=0.0 if is_deferred else 1.0,
            score_cart_state=0.0,
            overall_confidence=0.0,
            status="ANOMALY_FLAGGED"
        )
        db.add(ver_event)
        db.flush()

        anomaly = AnomalyEvent(
            session_id=session_id,
            verification_event_id=ver_event.id,
            anomaly_type=anomaly_type,
            description=description,
            severity=severity,
            status="DETECTED"
        )
        db.add(anomaly)
        db.commit()
        db.refresh(anomaly)

        return {
            "verification_event_id": ver_event.id,
            "anomaly_id": anomaly.id,
            "event_type": "ANOMALY_EVENT",
            "anomaly_type": anomaly_type,
            "severity": severity,
            "description": description,
            "observed_weight_delta": observed_delta,
            "expected_weight": expected_delta,
            "overall_confidence": 0.0,
            "status": "FLAGGED",
            "requires_action": not is_deferred
        }

# Global singleton
sensor_fusion_engine = MultimodalVerificationEngine()
