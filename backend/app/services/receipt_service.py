"""
TrolleyWise Electronic Receipt Service
Section 11:
- Generates compliant Indian GST Tax Invoices
- Itemized breakdown: HSN code, CGST, SGST, Quantity, Price, Discounts
- Embeds verification QR code
- Produces downloadable PDF via ReportLab and formatted text/JSON
"""

import os
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing

from backend.app.core.config import settings
from backend.app.db.models import BillingTransaction, Receipt, Store

class ReceiptService:
    def __init__(self):
        self.output_dir = settings.RECEIPT_OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_receipt(self, db: Session, transaction_id: int) -> Dict[str, Any]:
        """
        Creates the official electronic receipt record and generates standard PDF invoice.
        """
        tx = db.query(BillingTransaction).filter(BillingTransaction.id == transaction_id).first()
        if not tx:
            raise ValueError(f"Transaction {transaction_id} not found.")

        # Check if receipt already generated
        existing_receipt = db.query(Receipt).filter(Receipt.transaction_id == tx.id).first()
        if existing_receipt:
            return {
                "receipt_id": existing_receipt.id,
                "receipt_number": existing_receipt.receipt_number,
                "pdf_path": existing_receipt.pdf_path,
                "pdf_url": f"/api/receipts/{tx.id}/pdf",
                "qr_token": existing_receipt.qr_verification_token
            }

        store = tx.session.store
        receipt_num = f"RCPT-{datetime.now().strftime('%Y%m')}-{tx.id:05d}"
        qr_token = f"TW-VERIFY-{uuid.uuid4().hex}"
        pdf_filename = f"{receipt_num}.pdf"
        pdf_path = os.path.join(self.output_dir, pdf_filename)

        # Generate PDF
        self._build_pdf(tx, store, receipt_num, qr_token, pdf_path)

        receipt = Receipt(
            transaction_id=tx.id,
            receipt_number=receipt_num,
            pdf_path=pdf_path,
            qr_verification_token=qr_token
        )
        db.add(receipt)
        db.commit()
        db.refresh(receipt)

        return {
            "receipt_id": receipt.id,
            "receipt_number": receipt.receipt_number,
            "pdf_path": receipt.pdf_path,
            "pdf_url": f"/api/receipts/{tx.id}/pdf",
            "qr_token": receipt.qr_verification_token
        }

    def _build_pdf(
        self,
        tx: BillingTransaction,
        store: Store,
        receipt_num: str,
        qr_token: str,
        filepath: str
    ):
        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        styles = getSampleStyleSheet()
        elements = []

        title_style = ParagraphStyle(
            'HeaderTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=colors.HexColor('#1E293B'),
            alignment=1
        )
        sub_style = ParagraphStyle(
            'HeaderSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#64748B'),
            alignment=1
        )
        body_style = ParagraphStyle(
            'ReceiptBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12
        )

        elements.append(Paragraph("TROLLEYWISE SMART RETAIL", title_style))
        elements.append(Paragraph(f"{store.name}<br/>{store.address}<br/>GSTIN: {settings.STORE_GSTIN}", sub_style))
        elements.append(Spacer(1, 15))

        # Meta info table
        created_str = tx.created_at.strftime("%d-%b-%Y %I:%M %p") if tx.created_at else ""
        meta_data = [
            [f"Invoice No: {tx.invoice_number}", f"Receipt No: {receipt_num}"],
            [f"Date: {created_str}", f"Trolley ID: {tx.session.trolley.device_uuid}"],
            [f"Payment Status: {tx.status}", f"Customer: {tx.session.customer.full_name if tx.session.customer else 'Guest'}"]
        ]
        meta_table = Table(meta_data, colWidths=[270, 270])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#334155')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 15))

        # Line items table
        headers = ["Item / Description", "HSN", "Qty", "Price", "Discount", "Tax", "Total"]
        table_rows = [headers]

        for item in tx.session.cart.items:
            hsn = item.product.category.hsn_code if item.product.category else "1905"
            line_disc = item.discount_snapshot * item.quantity
            line_tax = (item.subtotal - line_disc) * Decimal(str(item.tax_rate_snapshot))
            line_total = (item.subtotal - line_disc) + line_tax
            table_rows.append([
                Paragraph(f"<b>{item.product.name}</b><br/><font color='#666'>SKU: {item.product.sku}</font>", body_style),
                hsn,
                str(item.quantity),
                f"Rs.{item.unit_price_snapshot:.2f}",
                f"Rs.{line_disc:.2f}",
                f"Rs.{line_tax:.2f}",
                f"Rs.{line_total:.2f}"
            ])

        items_table = Table(table_rows, colWidths=[200, 50, 35, 60, 60, 65, 70])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#CBD5E1')),
            ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 15))

        # Totals breakdown
        totals_data = [
            ["Subtotal:", f"Rs.{tx.subtotal:.2f}"],
            ["Discounts & Offers:", f"- Rs.{tx.total_discount:.2f}"],
            ["Taxable Value:", f"Rs.{tx.taxable_amount:.2f}"],
            ["CGST (Central Tax):", f"Rs.{tx.cgst_amount:.2f}"],
            ["SGST (State Tax):", f"Rs.{tx.sgst_amount:.2f}"],
            ["Total Applicable GST:", f"Rs.{tx.total_tax:.2f}"],
            ["FINAL AMOUNT PAID:", f"Rs.{tx.final_amount:.2f}"]
        ]
        totals_table = Table(totals_data, colWidths=[380, 160])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -2), 9),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#0F172A')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(totals_table)
        elements.append(Spacer(1, 20))

        # Verification QR Code
        qr_drawing = qr.QrCodeWidget(f"https://trolleywise.store/verify/{qr_token}")
        qr_drawing.barWidth = 70
        qr_drawing.barHeight = 70
        qr_drawing.qrVersion = 1
        d = Drawing(70, 70)
        d.add(qr_drawing)
        elements.append(d)
        elements.append(Paragraph(f"<font size=7 color='#64748B'>Official Tax Invoice. Scan to verify authenticity. Token: {qr_token[:18]}...</font>", sub_style))

        doc.build(elements)

# Global singleton
receipt_service = ReceiptService()
