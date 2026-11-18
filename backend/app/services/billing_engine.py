"""
TrolleyWise Automatic Live Billing Engine
Section 6:
- Pure Decimal arithmetic for monetary precision (never floats)
- Dynamic cart state management triggered by multimodal verification events
- Price, tax, and discount snapshotting to protect active transactions
- Promotional coupons, loyalty points, and store discount rules
- Budget tracking and threshold alerts
- Real-time notification dispatch
"""

import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.decimal_utils import to_decimal, calculate_line_item, TW_PRECISION
from backend.app.db.models import (
    ShoppingSession, DigitalCart, CartItem, ProductCatalog, ProductPrice,
    BillingTransaction, Promotion, DiscountRule, AnomalyEvent
)

class AutomaticBillingEngine:
    def get_or_create_cart(self, db: Session, session_id: int) -> DigitalCart:
        session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
        if not session:
            raise ValueError(f"Invalid session ID: {session_id}")

        if not session.cart:
            cart = DigitalCart(session_id=session.id, version=1, total_weight_grams=0.0, status="ACTIVE")
            db.add(cart)
            db.commit()
            db.refresh(cart)
            return cart
        return session.cart

    def add_verified_product(
        self,
        db: Session,
        session_id: int,
        product_id: int,
        verified_event_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Commits a verified product insertion to the digital cart and updates billing.
        Creates price snapshot and updates cart version atomically within a DB transaction.
        """
        session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found.")

        if session.status != "ACTIVE":
            raise ValueError(f"Cannot add items to session in status: {session.status}")

        cart = self.get_or_create_cart(db, session_id)
        if cart.status == "FROZEN":
            raise ValueError("Cart is frozen for checkout. Modification not allowed.")

        product = db.query(ProductCatalog).filter(ProductCatalog.id == product_id).first()
        if not product or not product.is_active:
            raise ValueError(f"Product ID {product_id} is inactive or invalid.")

        # Obtain current store price snapshot
        current_price = db.query(ProductPrice).filter(
            ProductPrice.product_id == product.id,
            ProductPrice.is_current == True
        ).first()

        unit_price = current_price.base_price if current_price else Decimal("50.00")
        tax_rate = product.category.default_tax_pct if product.category else settings.DEFAULT_GST_RATE

        # Check if product is already in cart
        cart_item = db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product.id
        ).first()

        if cart_item:
            cart_item.quantity += 1
            cart_item.subtotal = (Decimal(cart_item.quantity) * cart_item.unit_price_snapshot).quantize(TW_PRECISION, rounding=ROUND_HALF_UP)
            cart_item.verified_event_id = verified_event_id
        else:
            cart_item = CartItem(
                cart_id=cart.id,
                product_id=product.id,
                quantity=1,
                unit_price_snapshot=unit_price,
                discount_snapshot=Decimal("0.00"),
                tax_rate_snapshot=tax_rate,
                subtotal=unit_price,
                verified_event_id=verified_event_id
            )
            db.add(cart_item)

        # Update cart total weight & version
        prod_weight = product.weight_record.expected_weight_grams if product.weight_record else 100.0
        cart.total_weight_grams = max(0.0, float(cart.total_weight_grams or 0.0) + prod_weight)
        cart.version += 1

        db.commit()

        # Recalculate financial bill
        bill_data = self.recalculate_bill(db, session_id)
        return bill_data

    def remove_verified_product(
        self,
        db: Session,
        session_id: int,
        product_id: int,
        verified_event_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Commits a verified product removal to the digital cart and updates billing.
        Atomically decrements or removes item and recalculates total.
        """
        session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found.")

        cart = self.get_or_create_cart(db, session_id)
        if cart.status == "FROZEN":
            raise ValueError("Cart is frozen for checkout.")

        cart_item = db.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product_id
        ).first()

        if not cart_item or cart_item.quantity <= 0:
            raise ValueError(f"Product {product_id} does not exist in cart.")

        product = cart_item.product
        prod_weight = product.weight_record.expected_weight_grams if product and product.weight_record else 100.0

        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.subtotal = (Decimal(cart_item.quantity) * cart_item.unit_price_snapshot).quantize(TW_PRECISION, rounding=ROUND_HALF_UP)
            cart_item.verified_event_id = verified_event_id
        else:
            db.delete(cart_item)

        cart.total_weight_grams = max(0.0, float(cart.total_weight_grams or 0.0) - prod_weight)
        cart.version += 1

        db.commit()

        # Recalculate financial bill
        bill_data = self.recalculate_bill(db, session_id)
        return bill_data

    def recalculate_bill(
        self,
        db: Session,
        session_id: int,
        coupon_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recalculates exact itemized subtotal, discounts, taxable base, CGST, SGST,
        final total, and budget margin using strict Decimal precision.
        """
        session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found.")

        cart = self.get_or_create_cart(db, session_id)
        cart_items = db.query(CartItem).filter(CartItem.cart_id == cart.id).all()

        total_subtotal = Decimal("0.00")
        total_item_discount = Decimal("0.00")
        total_taxable = Decimal("0.00")
        total_cgst = Decimal("0.00")
        total_sgst = Decimal("0.00")
        total_tax = Decimal("0.00")
        
        display_items = []

        for item in cart_items:
            line = calculate_line_item(
                quantity=item.quantity,
                unit_price=item.unit_price_snapshot,
                discount_per_unit=item.discount_snapshot,
                tax_rate=item.tax_rate_snapshot
            )
            total_subtotal += line["line_subtotal"]
            total_item_discount += line["line_discount"]
            total_taxable += line["taxable_amount"]
            total_cgst += line["cgst"]
            total_sgst += line["sgst"]
            total_tax += line["total_tax"]

            display_items.append({
                "cart_item_id": item.id,
                "product_id": item.product_id,
                "sku": item.product.sku,
                "name": item.product.name,
                "brand": item.product.brand,
                "image_url": item.product.image_url,
                "quantity": item.quantity,
                "unit_price": str(line["unit_price"]),
                "discount_per_unit": str(line["discount_per_unit"]),
                "subtotal": str(line["line_subtotal"]),
                "taxable_amount": str(line["taxable_amount"]),
                "cgst": str(line["cgst"]),
                "sgst": str(line["sgst"]),
                "tax_rate": float(line["tax_rate"]),
                "line_final": str(line["line_final"])
            })

        # Evaluate Cart-level Promotions & Coupons
        promo_discount = Decimal("0.00")
        applied_promo_name = None

        if coupon_code:
            promo = db.query(Promotion).filter(
                Promotion.promo_code == coupon_code.strip().upper(),
                Promotion.is_active == True
            ).first()
            if promo:
                for rule in promo.discount_rules:
                    min_val = rule.min_cart_value or Decimal("0.00")
                    if total_subtotal >= min_val:
                        pct = Decimal(str(rule.discount_pct / 100.0))
                        calc_disc = (total_taxable * pct).quantize(TW_PRECISION, rounding=ROUND_HALF_UP)
                        if rule.max_discount_amount and calc_disc > rule.max_discount_amount:
                            calc_disc = rule.max_discount_amount
                        promo_discount = calc_disc
                        applied_promo_name = promo.name
                        break

        total_discount = total_item_discount + promo_discount
        if promo_discount > Decimal("0.00"):
            # Recalculate tax with promotional discount
            adjusted_taxable = max(Decimal("0.00"), total_taxable - promo_discount)
            avg_tax_rate = Decimal(str(settings.DEFAULT_GST_RATE))
            total_cgst = (adjusted_taxable * (avg_tax_rate / Decimal("2.0"))).quantize(TW_PRECISION, rounding=ROUND_HALF_UP)
            total_sgst = (adjusted_taxable * (avg_tax_rate / Decimal("2.0"))).quantize(TW_PRECISION, rounding=ROUND_HALF_UP)
            total_tax = total_cgst + total_sgst
            final_amount = adjusted_taxable + total_tax
        else:
            final_amount = total_taxable + total_tax

        # Customer Budget Tracking
        budget_limit = session.budget_limit or (
            Decimal(str(session.customer.preferences.get("budget_limit", 0)))
            if session.customer and isinstance(session.customer.preferences, dict)
            else None
        )
        remaining_budget = None
        is_over_budget = False
        if budget_limit:
            budget_limit = to_decimal(budget_limit)
            remaining_budget = str(budget_limit - final_amount)
            is_over_budget = final_amount > budget_limit

        # Persist / Update BillingTransaction
        tx = session.billing_transaction
        if not tx:
            invoice_num = f"TW-INV-{session.id:04d}-{uuid.uuid4().hex[:6].upper()}"
            tx = BillingTransaction(
                session_id=session.id,
                cart_id=cart.id,
                invoice_number=invoice_num,
                subtotal=total_subtotal,
                total_discount=total_discount,
                taxable_amount=max(Decimal("0.00"), total_taxable - promo_discount),
                total_tax=total_tax,
                cgst_amount=total_cgst,
                sgst_amount=total_sgst,
                final_amount=final_amount,
                status="DRAFT"
            )
            db.add(tx)
        else:
            if tx.status == "DRAFT":
                tx.subtotal = total_subtotal
                tx.total_discount = total_discount
                tx.taxable_amount = max(Decimal("0.00"), total_taxable - promo_discount)
                tx.total_tax = total_tax
                tx.cgst_amount = total_cgst
                tx.sgst_amount = total_sgst
                tx.final_amount = final_amount

        db.commit()
        db.refresh(tx)

        return {
            "session_id": session.id,
            "cart_id": cart.id,
            "cart_version": cart.version,
            "invoice_number": tx.invoice_number,
            "items_count": sum(item.quantity for item in cart_items),
            "items": display_items,
            "subtotal": str(total_subtotal),
            "total_discount": str(total_discount),
            "applied_promo": applied_promo_name,
            "taxable_amount": str(tx.taxable_amount),
            "cgst_amount": str(total_cgst),
            "sgst_amount": str(total_sgst),
            "total_tax": str(total_tax),
            "final_amount": str(final_amount),
            "currency": settings.STORE_CURRENCY,
            "currency_symbol": settings.STORE_CURRENCY_SYMBOL,
            "budget_limit": str(budget_limit) if budget_limit else None,
            "remaining_budget": remaining_budget,
            "is_over_budget": is_over_budget,
            "total_weight_grams": cart.total_weight_grams,
            "cart_status": cart.status
        }

    def freeze_cart_for_checkout(self, db: Session, session_id: int) -> BillingTransaction:
        """
        Freezes cart version for checkout and ensures no unresolved anomalies block checkout.
        """
        # Check for active anomalies
        unresolved = db.query(AnomalyEvent).filter(
            AnomalyEvent.session_id == session_id,
            AnomalyEvent.status.in_(["DETECTED", "INVESTIGATING"])
        ).count()
        if unresolved > 0:
            raise ValueError(f"Cannot checkout: {unresolved} unresolved anomaly events require staff or customer resolution.")

        cart = self.get_or_create_cart(db, session_id)
        if not cart.items:
            raise ValueError("Cannot checkout with an empty cart.")

        cart.status = "FROZEN"
        session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
        session.status = "CHECKOUT_PENDING"

        tx = session.billing_transaction
        if tx:
            tx.status = "FROZEN"

        db.commit()
        return tx

# Global singleton
billing_engine = AutomaticBillingEngine()
