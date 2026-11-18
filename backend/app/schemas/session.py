from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel

class SessionCreate(BaseModel):
    trolley_uuid: str = "TROLLEY-01"
    customer_id: Optional[int] = None
    store_code: str = "TW-STORE-001"
    budget_limit: Optional[Decimal] = None

class SessionOut(BaseModel):
    id: int
    session_token: str
    trolley_uuid: str
    customer_name: Optional[str]
    store_code: str
    status: str
    budget_limit: Optional[Decimal]
    started_at: str

    class Config:
        from_attributes = True

class SessionEventCreate(BaseModel):
    event_type: str # MANUAL_SCAN, BARCODE_SCAN, SENSOR_TRIGGER, ASSISTANCE_REQUEST
    payload: Optional[dict] = None
