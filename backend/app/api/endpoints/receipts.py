import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.db.models import BillingTransaction, Receipt
from backend.app.services.receipt_service import receipt_service

router = APIRouter()

@router.get("/{transaction_id}")
def get_receipt(transaction_id: int, db: Session = Depends(get_db)):
    tx = db.query(BillingTransaction).filter(BillingTransaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    receipt = db.query(Receipt).filter(Receipt.transaction_id == tx.id).first()
    if not receipt:
        receipt_info = receipt_service.generate_receipt(db, transaction_id)
        return receipt_info

    return {
        "receipt_id": receipt.id,
        "receipt_number": receipt.receipt_number,
        "transaction_id": tx.id,
        "invoice_number": tx.invoice_number,
        "amount_paid": str(tx.final_amount),
        "pdf_url": f"/api/receipts/{tx.id}/pdf",
        "qr_verification_token": receipt.qr_verification_token,
        "generated_at": receipt.generated_at.isoformat() if receipt.generated_at else None
    }

@router.get("/{transaction_id}/pdf")
def download_receipt_pdf(transaction_id: int, db: Session = Depends(get_db)):
    tx = db.query(BillingTransaction).filter(BillingTransaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    receipt = db.query(Receipt).filter(Receipt.transaction_id == tx.id).first()
    if not receipt or not os.path.exists(receipt.pdf_path):
        receipt_info = receipt_service.generate_receipt(db, transaction_id)
        pdf_path = receipt_info["pdf_path"]
    else:
        pdf_path = receipt.pdf_path

    return FileResponse(
        path=pdf_path,
        filename=os.path.basename(pdf_path),
        media_type="application/pdf"
    )
