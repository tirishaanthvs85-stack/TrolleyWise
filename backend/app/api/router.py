from fastapi import APIRouter
from backend.app.api.endpoints import (
    products, trolley, sessions, verification,
    billing, payments, receipts, inventory, retailer, ws
)

api_router = APIRouter()

api_router.include_router(products.router, prefix="/products", tags=["Products"])
api_router.include_router(trolley.router, prefix="/trolley", tags=["Trolley"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(verification.router, prefix="/verification", tags=["Verification"])
api_router.include_router(verification.router, tags=["Anomalies"]) # /api/anomalies
api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(receipts.router, prefix="/receipts", tags=["Receipts"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
api_router.include_router(retailer.router, prefix="/retailer", tags=["Retailer"])
api_router.include_router(ws.router, prefix="/ws", tags=["WebSocket"])
