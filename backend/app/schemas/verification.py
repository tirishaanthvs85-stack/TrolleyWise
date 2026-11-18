from typing import Optional, Dict, Any
from pydantic import BaseModel

class VerificationEvaluateRequest(BaseModel):
    session_id: int
    visual_event: Optional[Dict[str, Any]] = None # {"sku": "TW-MILK-001", "confidence": 0.92, "direction": "INWARD"}
    sensor_reading_pre: Dict[str, Any] # {"filtered_weight_grams": 0.0, "is_stable": True}
    sensor_reading_post: Dict[str, Any] # {"filtered_weight_grams": 515.0, "is_stable": True, "imu": {"is_moving": False}}

class AnomalyResolveRequest(BaseModel):
    resolution_action: str # CUSTOMER_CONFIRMED, STAFF_OVERRIDE, DISMISSED, CORRECTED
    resolved_by: str = "STORE_STAFF"
    resolution_notes: Optional[str] = None
