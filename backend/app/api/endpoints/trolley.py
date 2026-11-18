from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.db.models import TrolleyDevice, Store, SensorReading, DeviceHealth
from backend.app.schemas.sensor import TrolleyRegistration, SensorDataIngest

router = APIRouter()

@router.post("/register")
def register_trolley(payload: TrolleyRegistration, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.store_code == payload.store_code).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store code not found")

    trolley = db.query(TrolleyDevice).filter(TrolleyDevice.device_uuid == payload.device_uuid).first()
    if not trolley:
        trolley = TrolleyDevice(
            device_uuid=payload.device_uuid,
            store_id=store.id,
            mac_address=payload.mac_address,
            ip_address=payload.ip_address,
            firmware_version=payload.firmware_version,
            status="IDLE"
        )
        db.add(trolley)
    else:
        trolley.mac_address = payload.mac_address or trolley.mac_address
        trolley.ip_address = payload.ip_address or trolley.ip_address
        trolley.firmware_version = payload.firmware_version
        trolley.last_heartbeat = datetime.now(timezone.utc)

    db.commit()
    db.refresh(trolley)
    return {
        "status": "REGISTERED",
        "device_id": trolley.id,
        "device_uuid": trolley.device_uuid,
        "store": store.name
    }

@router.get("/{trolley_uuid}/status")
def get_trolley_status(trolley_uuid: str, db: Session = Depends(get_db)):
    trolley = db.query(TrolleyDevice).filter(TrolleyDevice.device_uuid == trolley_uuid).first()
    if not trolley:
        raise HTTPException(status_code=404, detail=f"Trolley {trolley_uuid} not found")

    last_reading = db.query(SensorReading).filter(SensorReading.trolley_id == trolley.id).order_by(SensorReading.timestamp.desc()).first()

    return {
        "device_uuid": trolley.device_uuid,
        "status": trolley.status,
        "battery_level": trolley.battery_level,
        "firmware_version": trolley.firmware_version,
        "last_heartbeat": trolley.last_heartbeat.isoformat() if trolley.last_heartbeat else None,
        "current_weight": last_reading.filtered_weight_grams if last_reading else 0.0,
        "is_moving": last_reading.is_moving if last_reading else False
    }

@router.post("/{trolley_uuid}/sensor-data")
def ingest_sensor_data(trolley_uuid: str, reading: SensorDataIngest, db: Session = Depends(get_db)):
    trolley = db.query(TrolleyDevice).filter(TrolleyDevice.device_uuid == trolley_uuid).first()
    if not trolley:
        raise HTTPException(status_code=404, detail=f"Trolley {trolley_uuid} not registered")

    now = datetime.now(timezone.utc)
    trolley.last_heartbeat = now

    imu = reading.imu
    reading_rec = SensorReading(
        trolley_id=trolley.id,
        session_id=reading.session_id,
        timestamp=now,
        raw_weight_grams=reading.raw_weight_grams,
        filtered_weight_grams=reading.filtered_weight_grams,
        is_stable=reading.is_stable,
        accel_x=imu.accel_x if imu else 0.0,
        accel_y=imu.accel_y if imu else 0.0,
        accel_z=imu.accel_z if imu else 9.81,
        gyro_x=imu.gyro_x if imu else 0.0,
        gyro_y=imu.gyro_y if imu else 0.0,
        gyro_z=imu.gyro_z if imu else 0.0,
        is_moving=imu.is_moving if imu else False
    )
    db.add(reading_rec)
    db.commit()

    return {"status": "INGESTED", "reading_id": reading_rec.id}
