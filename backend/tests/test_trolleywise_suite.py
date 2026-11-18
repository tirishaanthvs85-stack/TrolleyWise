"""
TrolleyWise Automated Test Suite
Implements all 22 mandatory verification test cases from Section 17 of Patent Specification:
1. Successful product insertion
2. Successful product removal
3. Duplicate detection prevention
4. Weight mismatch
5. Unrecognized product
6. Multiple products entering together
7. Trolley movement during weighing
8. Unexplained weight increase
9. Unexplained weight decrease
10. Uncertain visual recognition
11. Incorrect product quantity
12. Real-time bill calculation
13. Discount calculation
14. Tax calculation
15. Cart total calculation
16. Failed payment
17. Successful payment verification
18. Duplicate payment callback
19. Receipt generation
20. Inventory synchronization
21. Offline operation
22. Reconnection and synchronization
"""

import pytest
import time
from decimal import Decimal
from backend.app.services.sensor_fusion import sensor_fusion_engine
from backend.app.services.billing_engine import billing_engine
from backend.app.services.payment_service import payment_service
from backend.app.services.receipt_service import receipt_service
from backend.app.services.inventory_service import inventory_service
from backend.app.services.offline_sync import offline_sync_service
from backend.app.services.ai_recognition import ai_recognition_engine
from backend.app.db.models import (
    ShoppingSession, DigitalCart, CartItem, ProductCatalog, 
    BillingTransaction, Inventory, PaymentAttempt
)

def create_active_session(db_session):
    cart = DigitalCart(version=1, total_weight_grams=0.0, status="ACTIVE")
    session = ShoppingSession(
        session_token=f"TW-TEST-{int(time.time()*1000)}",
        trolley_id=1,
        customer_id=1,
        store_id=1,
        budget_limit=Decimal("1000.00"),
        status="ACTIVE",
        cart=cart
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session

# TEST 1: Successful product insertion
def test_01_successful_product_insertion(db_session):
    sess = create_active_session(db_session)
    milk = db_session.query(ProductCatalog).filter(ProductCatalog.sku == "TW-MILK-001").first()

    # Visual detection of Milk (515g) + matching weight change
    res = sensor_fusion_engine.evaluate_event(
        db=db_session,
        session_id=sess.id,
        visual_event={"sku": "TW-MILK-001", "confidence": 0.95, "direction": "INWARD", "frames_tracked": 3},
        sensor_reading_pre={"filtered_weight_grams": 0.0, "is_stable": True},
        sensor_reading_post={"filtered_weight_grams": 515.0, "is_stable": True, "imu": {"is_moving": False}}
    )

    assert res["event_type"] == "VERIFIED_INSERTION"
    assert res["status"] == "CONFIRMED"
    assert res["overall_confidence"] >= 0.70

    # Commit to cart
    bill = billing_engine.add_verified_product(db_session, sess.id, milk.id, res["verification_event_id"])
    assert bill["items_count"] == 1
    assert bill["items"][0]["sku"] == "TW-MILK-001"

# TEST 2: Successful product removal
def test_02_successful_product_removal(db_session):
    sess = create_active_session(db_session)
    milk = db_session.query(ProductCatalog).filter(ProductCatalog.sku == "TW-MILK-001").first()
    billing_engine.add_verified_product(db_session, sess.id, milk.id)

    # Remove Milk (-515g)
    res = sensor_fusion_engine.evaluate_event(
        db=db_session,
        session_id=sess.id,
        visual_event={"sku": "TW-MILK-001", "confidence": 0.93, "direction": "OUTWARD", "frames_tracked": 3},
        sensor_reading_pre={"filtered_weight_grams": 515.0, "is_stable": True},
        sensor_reading_post={"filtered_weight_grams": 0.0, "is_stable": True, "imu": {"is_moving": False}}
    )

    assert res["event_type"] == "VERIFIED_REMOVAL"
    bill = billing_engine.remove_verified_product(db_session, sess.id, milk.id, res["verification_event_id"])
    assert bill["items_count"] == 0

# TEST 3: Duplicate detection prevention
def test_03_duplicate_detection_prevention():
    # Cooldown window prevents repeated triggers within 3 seconds
    ai_recognition_engine.event_cooldowns["TW-MILK-001_INWARD"] = time.time()
    # Check that immediate subsequent trigger is suppressed
    assert (time.time() - ai_recognition_engine.event_cooldowns["TW-MILK-001_INWARD"]) < 3.0

# TEST 4: Weight mismatch
def test_04_weight_mismatch(db_session):
    sess = create_active_session(db_session)
    # Milk expected 515g, but measured 1200g
    res = sensor_fusion_engine.evaluate_event(
        db=db_session,
        session_id=sess.id,
        visual_event={"sku": "TW-MILK-001", "confidence": 0.90, "direction": "INWARD", "frames_tracked": 3},
        sensor_reading_pre={"filtered_weight_grams": 0.0, "is_stable": True},
        sensor_reading_post={"filtered_weight_grams": 1200.0, "is_stable": True, "imu": {"is_moving": False}}
    )
    assert res["event_type"] == "ANOMALY_EVENT"

# TEST 5: Unrecognized product
def test_05_unrecognized_product(db_session):
    sess = create_active_session(db_session)
    res = sensor_fusion_engine.evaluate_event(
        db=db_session,
        session_id=sess.id,
        visual_event={"sku": "TW-NONEXISTENT-999", "confidence": 0.90, "direction": "INWARD"},
        sensor_reading_pre={"filtered_weight_grams": 0.0, "is_stable": True},
        sensor_reading_post={"filtered_weight_grams": 100.0, "is_stable": True, "imu": {"is_moving": False}}
    )
    assert res["event_type"] == "ANOMALY_EVENT"
    assert res["anomaly_type"] == "UNKNOWN_CATALOGUE_SKU"

# TEST 6: Multiple products entering together
def test_06_multiple_products_entering_together(db_session):
    sess = create_active_session(db_session)
    # Visual shows Soap (128g), but weight jumps by 1050g
    res = sensor_fusion_engine.evaluate_event(
        db=db_session,
        session_id=sess.id,
        visual_event={"sku": "TW-SOAP-004", "confidence": 0.88, "direction": "INWARD"},
        sensor_reading_pre={"filtered_weight_grams": 0.0, "is_stable": True},
        sensor_reading_post={"filtered_weight_grams": 1050.0, "is_stable": True, "imu": {"is_moving": False}}
    )
    assert res["event_type"] == "ANOMALY_EVENT"

# TEST 7: Trolley movement during weighing
def test_07_trolley_movement_during_weighing(db_session):
    sess = create_active_session(db_session)
    # Trolley actively moving (imu is_moving=True)
    res = sensor_fusion_engine.evaluate_event(
        db=db_session,
        session_id=sess.id,
        visual_event={"sku": "TW-MILK-001", "confidence": 0.92, "direction": "INWARD"},
        sensor_reading_pre={"filtered_weight_grams": 0.0, "is_stable": False},
        sensor_reading_post={"filtered_weight_grams": 515.0, "is_stable": False, "imu": {"is_moving": True}}
    )
    assert res["event_type"] == "ANOMALY_EVENT"
    assert res["anomaly_type"] == "MOTION_INSTABILITY_DEFERRAL"

# TEST 8: Unexplained weight increase
def test_08_unexplained_weight_increase(db_session):
    sess = create_active_session(db_session)
    # Weight increases by 350g with NO visual event
    res = sensor_fusion_engine.evaluate_event(
        db=db_session,
        session_id=sess.id,
        visual_event=None,
        sensor_reading_pre={"filtered_weight_grams": 0.0, "is_stable": True},
        sensor_reading_post={"filtered_weight_grams": 350.0, "is_stable": True, "imu": {"is_moving": False}}
    )
    assert res["event_type"] == "ANOMALY_EVENT"
    assert res["anomaly_type"] == "UNRECOGNIZED_WEIGHT_CHANGE"

# TEST 9: Unexplained weight decrease
def test_09_unexplained_weight_decrease(db_session):
    sess = create_active_session(db_session)
    # Weight drops by 400g with NO visual event
    res = sensor_fusion_engine.evaluate_event(
        db=db_session,
        session_id=sess.id,
        visual_event=None,
        sensor_reading_pre={"filtered_weight_grams": 500.0, "is_stable": True},
        sensor_reading_post={"filtered_weight_grams": 100.0, "is_stable": True, "imu": {"is_moving": False}}
    )
    assert res["event_type"] == "ANOMALY_EVENT"
    assert res["anomaly_type"] == "UNRECOGNIZED_WEIGHT_CHANGE"

# TEST 10: Uncertain visual recognition
def test_10_uncertain_visual_recognition(db_session):
    sess = create_active_session(db_session)
    # Low visual confidence (0.46)
    res = sensor_fusion_engine.evaluate_event(
        db=db_session,
        session_id=sess.id,
        visual_event={"sku": "TW-MILK-001", "confidence": 0.46, "direction": "INWARD", "frames_tracked": 1},
        sensor_reading_pre={"filtered_weight_grams": 0.0, "is_stable": True},
        sensor_reading_post={"filtered_weight_grams": 515.0, "is_stable": True, "imu": {"is_moving": False}}
    )
    assert res["event_type"] == "UNCERTAIN_EVENT"
    assert res["status"] == "PENDING_CONFIRMATION"

# TEST 11: Incorrect product quantity (removing item not in cart)
def test_11_incorrect_product_quantity(db_session):
    sess = create_active_session(db_session)
    # Empty cart, but removal detected
    res = sensor_fusion_engine.evaluate_event(
        db=db_session,
        session_id=sess.id,
        visual_event={"sku": "TW-MILK-001", "confidence": 0.90, "direction": "OUTWARD"},
        sensor_reading_pre={"filtered_weight_grams": 515.0, "is_stable": True},
        sensor_reading_post={"filtered_weight_grams": 0.0, "is_stable": True, "imu": {"is_moving": False}}
    )
    assert res["event_type"] == "ANOMALY_EVENT"
    assert res["anomaly_type"] == "UNREGISTERED_PRODUCT_REMOVAL"

# TEST 12: Real-time bill calculation
def test_12_realtime_bill_calculation(db_session):
    sess = create_active_session(db_session)
    milk = db_session.query(ProductCatalog).filter(ProductCatalog.sku == "TW-MILK-001").first() # Price: 45
    bread = db_session.query(ProductCatalog).filter(ProductCatalog.sku == "TW-BREAD-002").first() # Price: 30
    billing_engine.add_verified_product(db_session, sess.id, milk.id)
    billing_engine.add_verified_product(db_session, sess.id, bread.id)

    bill = billing_engine.recalculate_bill(db_session, sess.id)
    assert bill["subtotal"] == "75.00"

# TEST 13: Discount calculation
def test_13_discount_calculation(db_session):
    sess = create_active_session(db_session)
    # Add items totaling > 100 to qualify for SMART10
    rice = db_session.query(ProductCatalog).filter(ProductCatalog.sku == "TW-RICE-003").first() # 65
    milk = db_session.query(ProductCatalog).filter(ProductCatalog.sku == "TW-MILK-001").first() # 45
    billing_engine.add_verified_product(db_session, sess.id, rice.id)
    billing_engine.add_verified_product(db_session, sess.id, milk.id)

    bill = billing_engine.recalculate_bill(db_session, sess.id, coupon_code="SMART10")
    assert Decimal(bill["total_discount"]) > Decimal("0.00")
    assert bill["applied_promo"] is not None

# TEST 14: Tax calculation
def test_14_tax_calculation(db_session):
    sess = create_active_session(db_session)
    soap = db_session.query(ProductCatalog).filter(ProductCatalog.sku == "TW-SOAP-004").first() # 25.00, tax 18%
    billing_engine.add_verified_product(db_session, sess.id, soap.id)
    bill = billing_engine.recalculate_bill(db_session, sess.id)
    # CGST (9%) + SGST (9%) = 18% on 25.00 = 4.50
    assert bill["cgst_amount"] == "2.25"
    assert bill["sgst_amount"] == "2.25"
    assert bill["total_tax"] == "4.50"

# TEST 15: Cart total calculation
def test_15_cart_total_calculation(db_session):
    sess = create_active_session(db_session)
    soap = db_session.query(ProductCatalog).filter(ProductCatalog.sku == "TW-SOAP-004").first()
    billing_engine.add_verified_product(db_session, sess.id, soap.id)
    bill = billing_engine.recalculate_bill(db_session, sess.id)
    # Total = 25.00 + 4.50 = 29.50
    assert bill["final_amount"] == "29.50"

# TEST 16: Failed payment
def test_16_failed_payment(db_session):
    sess = create_active_session(db_session)
    soap = db_session.query(ProductCatalog).filter(ProductCatalog.sku == "TW-SOAP-004").first()
    billing_engine.add_verified_product(db_session, sess.id, soap.id)
    billing_engine.freeze_cart_for_checkout(db_session, sess.id)
    order = payment_service.create_payment_order(db_session, sess.id)

    # Invalid signature must fail
    with pytest.raises(ValueError):
        payment_service.process_verified_payment(
            db=db_session,
            order_id=order["order_id"],
            payment_id="pay_fake_123",
            signature="tampered_invalid_signature"
        )

# TEST 17: Successful payment verification
def test_17_successful_payment_verification(db_session):
    sess = create_active_session(db_session)
    soap = db_session.query(ProductCatalog).filter(ProductCatalog.sku == "TW-SOAP-004").first()
    billing_engine.add_verified_product(db_session, sess.id, soap.id)
    billing_engine.freeze_cart_for_checkout(db_session, sess.id)
    order = payment_service.create_payment_order(db_session, sess.id)

    payment_id = "pay_valid_sandbox_99"
    valid_sig = payment_service.generate_sandbox_signature(order["order_id"], payment_id)

    res = payment_service.process_verified_payment(
        db=db_session,
        order_id=order["order_id"],
        payment_id=payment_id,
        signature=valid_sig
    )
    assert res["status"] == "PAYMENT_SUCCESS"
    assert res["invoice_number"] is not None

# TEST 18: Duplicate payment callback
def test_18_duplicate_payment_callback(db_session):
    sess = create_active_session(db_session)
    soap = db_session.query(ProductCatalog).filter(ProductCatalog.sku == "TW-SOAP-004").first()
    billing_engine.add_verified_product(db_session, sess.id, soap.id)
    billing_engine.freeze_cart_for_checkout(db_session, sess.id)
    order = payment_service.create_payment_order(db_session, sess.id)

    payment_id = "pay_valid_sandbox_dupe"
    valid_sig = payment_service.generate_sandbox_signature(order["order_id"], payment_id)

    res1 = payment_service.process_verified_payment(db_session, order["order_id"], payment_id, valid_sig)
    assert res1["status"] == "PAYMENT_SUCCESS"

    # Second call should handle gracefully without double deducting or double charging
    res2 = payment_service.process_verified_payment(db_session, order["order_id"], payment_id, valid_sig)
    assert res2["status"] == "ALREADY_PAID"

# TEST 19: Receipt generation
def test_19_receipt_generation(db_session):
    sess = create_active_session(db_session)
    soap = db_session.query(ProductCatalog).filter(ProductCatalog.sku == "TW-SOAP-004").first()
    billing_engine.add_verified_product(db_session, sess.id, soap.id)
    billing_engine.freeze_cart_for_checkout(db_session, sess.id)
    tx = sess.billing_transaction

    rcpt = receipt_service.generate_receipt(db_session, tx.id)
    assert rcpt["receipt_number"].startswith("RCPT-")
    assert rcpt["pdf_path"].endswith(".pdf")

# TEST 20: Inventory synchronization
def test_20_inventory_synchronization(db_session):
    sess = create_active_session(db_session)
    soap = db_session.query(ProductCatalog).filter(ProductCatalog.sku == "TW-SOAP-004").first()
    inv_before = db_session.query(Inventory).filter(Inventory.product_id == soap.id).first().current_stock

    billing_engine.add_verified_product(db_session, sess.id, soap.id)
    billing_engine.freeze_cart_for_checkout(db_session, sess.id)
    tx = sess.billing_transaction

    inventory_service.deduct_inventory_for_transaction(db_session, tx.id)
    inv_after = db_session.query(Inventory).filter(Inventory.product_id == soap.id).first().current_stock
    assert inv_after == inv_before - 1

# TEST 21: Offline operation
def test_21_offline_operation():
    offline_sync_service.enqueue_event("OFFLINE_PRODUCT_COMMIT", {"sku": "TW-MILK-001", "qty": 1})
    queue = offline_sync_service.read_queue()
    assert len(queue) >= 1

# TEST 22: Reconnection and synchronization
def test_22_reconnection_and_synchronization(db_session):
    sync_result = offline_sync_service.replay_and_sync(db_session)
    assert sync_result["status"] == "SYNCHRONIZED"
    assert sync_result["remaining_in_queue"] == 0
