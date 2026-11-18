from typing import Optional, Dict, Any
from pydantic import BaseModel

class IMUData(BaseModel):
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 9.81
    gyro_x: float = 0.0
    gyro_y: float = 0.0
    gyro_z: float = 0.0
    is_moving: bool = False

class SensorDataIngest(BaseModel):
    device_uuid: str
    session_id: Optional[int] = None
    raw_weight_grams: float
    filtered_weight_grams: float
    is_stable: bool = True
    imu: Optional[IMUData] = None

class TrolleyRegistration(BaseModel):
    device_uuid: str
    store_code: str = "TW-STORE-001"
    mac_address: Optional[str] = None
    ip_address: Optional[str] = None
    firmware_version: str = "2.4.1"
