from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.services.inventory_service import inventory_service
from backend.app.services.offline_sync import offline_sync_service

router = APIRouter()

@router.get("")
def get_inventory(store_id: int = 1, db: Session = Depends(get_db)):
    return inventory_service.get_inventory_status(db, store_id)

@router.post("/synchronize")
def synchronize_inventory(db: Session = Depends(get_db)):
    """
    Synchronizes local edge offline queue with central inventory ledger.
    """
    sync_result = offline_sync_service.replay_and_sync(db)
    return sync_result
