from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, 
    Text, Numeric, Index, Enum
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

# 1. Users
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="CUSTOMER", nullable=False) # CUSTOMER, CASHIER, STORE_MANAGER, ADMIN
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    customer = relationship("Customer", back_populates="user", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="user")

# 2. Customers
class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    phone_number = Column(String(20), index=True, nullable=False)
    full_name = Column(String(150), nullable=False)
    loyalty_member = Column(Boolean, default=False)
    preferences = Column(Text, nullable=True) # JSON or text string
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="customer")
    loyalty_account = relationship("LoyaltyAccount", back_populates="customer", uselist=False)
    sessions = relationship("ShoppingSession", back_populates="customer")

# 3. Retailers
class Retailer(Base):
    __tablename__ = "retailers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    legal_name = Column(String(255), nullable=False)
    tax_identifier = Column(String(50), unique=True, nullable=False) # GSTIN
    address = Column(Text, nullable=False)
    contact_email = Column(String(150), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    stores = relationship("Store", back_populates="retailer")

# 4. Stores
class Store(Base):
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True, index=True)
    retailer_id = Column(Integer, ForeignKey("retailers.id"), nullable=False)
    store_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    address = Column(Text, nullable=False)
    currency = Column(String(10), default="INR")
    tax_rate_default = Column(Float, default=0.18)
    created_at = Column(DateTime, default=utc_now)

    retailer = relationship("Retailer", back_populates="stores")
    trolleys = relationship("TrolleyDevice", back_populates="store")
    inventories = relationship("Inventory", back_populates="store")
    sessions = relationship("ShoppingSession", back_populates="store")

# 5. Trolley Devices
class TrolleyDevice(Base):
    __tablename__ = "trolley_devices"
    id = Column(Integer, primary_key=True, index=True)
    device_uuid = Column(String(100), unique=True, index=True, nullable=False) # e.g. TROLLEY-01
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    mac_address = Column(String(50), nullable=True)
    ip_address = Column(String(50), nullable=True)
    status = Column(String(50), default="IDLE") # IDLE, SHOPPING, MAINTENANCE, OFFLINE
    firmware_version = Column(String(50), default="1.0.0")
    battery_level = Column(Float, default=100.0)
    last_heartbeat = Column(DateTime, default=utc_now)

    store = relationship("Store", back_populates="trolleys")
    sessions = relationship("ShoppingSession", back_populates="trolley")
    sensor_readings = relationship("SensorReading", back_populates="trolley")
    camera_events = relationship("CameraEvent", back_populates="trolley")
    device_health_logs = relationship("DeviceHealth", back_populates="trolley")

# 6. Product Categories
class ProductCategory(Base):
    __tablename__ = "product_categories"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    hsn_code = Column(String(50), default="1905")
    default_tax_pct = Column(Float, default=0.18)

    products = relationship("ProductCatalog", back_populates="category")

# 7. Product Catalog
class ProductCatalog(Base):
    __tablename__ = "product_catalog"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(200), index=True, nullable=False)
    brand = Column(String(100), default="General")
    category_id = Column(Integer, ForeignKey("product_categories.id"), nullable=False)
    barcode = Column(String(100), index=True, nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    category = relationship("ProductCategory", back_populates="products")
    price_records = relationship("ProductPrice", back_populates="product")
    weight_record = relationship("ProductWeight", back_populates="product", uselist=False)
    inventories = relationship("Inventory", back_populates="product")

# 8. Product Prices
class ProductPrice(Base):
    __tablename__ = "product_prices"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("product_catalog.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    base_price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="INR")
    valid_from = Column(DateTime, default=utc_now)
    valid_to = Column(DateTime, nullable=True)
    is_current = Column(Boolean, default=True, index=True)

    product = relationship("ProductCatalog", back_populates="price_records")

# 9. Product Weights
class ProductWeight(Base):
    __tablename__ = "product_weights"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("product_catalog.id"), nullable=False, unique=True)
    expected_weight_grams = Column(Float, nullable=False) # e.g. 500.0g
    weight_tolerance_grams = Column(Float, default=20.0) # +/- tolerance
    calibration_date = Column(DateTime, default=utc_now)

    product = relationship("ProductCatalog", back_populates="weight_record")

# 10. Inventory
class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("product_catalog.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    current_stock = Column(Integer, default=0, nullable=False)
    reserved_stock = Column(Integer, default=0, nullable=False)
    min_threshold = Column(Integer, default=10)
    last_updated = Column(DateTime, default=utc_now, onupdate=utc_now)

    product = relationship("ProductCatalog", back_populates="inventories")
    store = relationship("Store", back_populates="inventories")

# 11. Promotions
class Promotion(Base):
    __tablename__ = "promotions"
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    name = Column(String(150), nullable=False)
    promo_code = Column(String(50), unique=True, index=True, nullable=True)
    promo_type = Column(String(50), default="PERCENTAGE") # PERCENTAGE, FIXED_DISCOUNT, BOGO
    value = Column(Float, default=0.0)
    start_date = Column(DateTime, default=utc_now)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    discount_rules = relationship("DiscountRule", back_populates="promotion")

# 12. Discount Rules
class DiscountRule(Base):
    __tablename__ = "discount_rules"
    id = Column(Integer, primary_key=True, index=True)
    promo_id = Column(Integer, ForeignKey("promotions.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product_catalog.id"), nullable=True)
    min_cart_value = Column(Numeric(10, 2), default=0.0)
    min_quantity = Column(Integer, default=1)
    discount_pct = Column(Float, default=0.0)
    max_discount_amount = Column(Numeric(10, 2), nullable=True)

    promotion = relationship("Promotion", back_populates="discount_rules")

# 13. Shopping Sessions
class ShoppingSession(Base):
    __tablename__ = "shopping_sessions"
    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String(100), unique=True, index=True, nullable=False)
    trolley_id = Column(Integer, ForeignKey("trolley_devices.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    status = Column(String(50), default="ACTIVE", index=True) # ACTIVE, CHECKOUT_PENDING, COMPLETED, ABANDONED
    budget_limit = Column(Numeric(10, 2), nullable=True)
    started_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)

    trolley = relationship("TrolleyDevice", back_populates="sessions")
    customer = relationship("Customer", back_populates="sessions")
    store = relationship("Store", back_populates="sessions")
    cart = relationship("DigitalCart", back_populates="session", uselist=False)
    billing_transaction = relationship("BillingTransaction", back_populates="session", uselist=False)
    verification_events = relationship("VerificationEvent", back_populates="session")
    anomaly_events = relationship("AnomalyEvent", back_populates="session")

# 14. Digital Carts
class DigitalCart(Base):
    __tablename__ = "digital_carts"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("shopping_sessions.id"), nullable=False, unique=True)
    version = Column(Integer, default=1, nullable=False)
    total_weight_grams = Column(Float, default=0.0)
    status = Column(String(50), default="ACTIVE") # ACTIVE, FROZEN, CHECKED_OUT
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    session = relationship("ShoppingSession", back_populates="cart")
    items = relationship("CartItem", back_populates="cart")

# 15. Cart Items
class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("digital_carts.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product_catalog.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price_snapshot = Column(Numeric(10, 2), nullable=False)
    discount_snapshot = Column(Numeric(10, 2), default=0.0)
    tax_rate_snapshot = Column(Float, default=0.18)
    subtotal = Column(Numeric(10, 2), nullable=False)
    added_at = Column(DateTime, default=utc_now)
    verified_event_id = Column(Integer, nullable=True)

    cart = relationship("DigitalCart", back_populates="items")
    product = relationship("ProductCatalog")

# 16. Sensor Readings
class SensorReading(Base):
    __tablename__ = "sensor_readings"
    id = Column(Integer, primary_key=True, index=True)
    trolley_id = Column(Integer, ForeignKey("trolley_devices.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("shopping_sessions.id"), nullable=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    raw_weight_grams = Column(Float, nullable=False)
    filtered_weight_grams = Column(Float, nullable=False)
    is_stable = Column(Boolean, default=True)
    accel_x = Column(Float, default=0.0)
    accel_y = Column(Float, default=0.0)
    accel_z = Column(Float, default=9.81)
    gyro_x = Column(Float, default=0.0)
    gyro_y = Column(Float, default=0.0)
    gyro_z = Column(Float, default=0.0)
    is_moving = Column(Boolean, default=False)

    trolley = relationship("TrolleyDevice", back_populates="sensor_readings")

# 17. Camera Events
class CameraEvent(Base):
    __tablename__ = "camera_events"
    id = Column(Integer, primary_key=True, index=True)
    trolley_id = Column(Integer, ForeignKey("trolley_devices.id"), nullable=False)
    camera_id = Column(String(50), default="CAM_TOP")
    timestamp = Column(DateTime, default=utc_now, index=True)
    frame_path = Column(String(500), nullable=True)
    movement_direction = Column(String(50), default="INWARD") # INWARD, OUTWARD, UNCERTAIN

    trolley = relationship("TrolleyDevice", back_populates="camera_events")
    detections = relationship("ProductDetection", back_populates="camera_event")

# 18. Product Detections
class ProductDetection(Base):
    __tablename__ = "product_detections"
    id = Column(Integer, primary_key=True, index=True)
    camera_event_id = Column(Integer, ForeignKey("camera_events.id"), nullable=False)
    sku = Column(String(100), nullable=False)
    class_id = Column(Integer, default=0)
    confidence = Column(Float, nullable=False)
    bbox_json = Column(Text, nullable=True)
    tracker_id = Column(Integer, nullable=True)

    camera_event = relationship("CameraEvent", back_populates="detections")

# 19. Verification Events
class VerificationEvent(Base):
    __tablename__ = "verification_events"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("shopping_sessions.id"), nullable=False)
    event_type = Column(String(50), nullable=False, index=True) # VERIFIED_INSERTION, VERIFIED_REMOVAL, UNCERTAIN_EVENT, ANOMALY_EVENT
    product_id = Column(Integer, ForeignKey("product_catalog.id"), nullable=True)
    observed_weight_delta = Column(Float, nullable=False)
    expected_weight = Column(Float, nullable=False)
    score_visual = Column(Float, default=0.0)
    score_weight = Column(Float, default=0.0)
    score_temporal = Column(Float, default=0.0)
    score_tracking = Column(Float, default=0.0)
    score_motion = Column(Float, default=0.0)
    score_cart_state = Column(Float, default=0.0)
    overall_confidence = Column(Float, nullable=False)
    status = Column(String(50), default="CONFIRMED")
    created_at = Column(DateTime, default=utc_now)

    session = relationship("ShoppingSession", back_populates="verification_events")
    product = relationship("ProductCatalog")

# 20. Anomaly Events
class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("shopping_sessions.id"), nullable=False)
    verification_event_id = Column(Integer, ForeignKey("verification_events.id"), nullable=True)
    anomaly_type = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    severity = Column(String(50), default="MEDIUM") # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(50), default="DETECTED", index=True) # DETECTED, INVESTIGATING, RESOLVED, DISMISSED
    resolution_notes = Column(Text, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    detected_at = Column(DateTime, default=utc_now)
    resolved_at = Column(DateTime, nullable=True)

    session = relationship("ShoppingSession", back_populates="anomaly_events")

# 21. Billing Transactions
class BillingTransaction(Base):
    __tablename__ = "billing_transactions"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("shopping_sessions.id"), nullable=False, unique=True)
    cart_id = Column(Integer, ForeignKey("digital_carts.id"), nullable=False)
    invoice_number = Column(String(100), unique=True, index=True, nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    total_discount = Column(Numeric(10, 2), default=0.0)
    taxable_amount = Column(Numeric(10, 2), nullable=False)
    total_tax = Column(Numeric(10, 2), nullable=False)
    cgst_amount = Column(Numeric(10, 2), nullable=False)
    sgst_amount = Column(Numeric(10, 2), nullable=False)
    final_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(50), default="DRAFT", index=True) # DRAFT, FROZEN, PAID, CANCELLED
    created_at = Column(DateTime, default=utc_now)

    session = relationship("ShoppingSession", back_populates="billing_transaction")
    payment_attempts = relationship("PaymentAttempt", back_populates="transaction")
    payment_records = relationship("PaymentRecord", back_populates="transaction")
    receipt = relationship("Receipt", back_populates="transaction", uselist=False)

# 22. Payment Attempts
class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("billing_transactions.id"), nullable=False)
    payment_method = Column(String(50), default="UPI") # UPI, CARD, WALLET
    provider = Column(String(50), default="RAZORPAY_SANDBOX")
    order_id = Column(String(100), unique=True, index=True, nullable=False)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(50), default="INITIATED", index=True) # INITIATED, SUCCESS, FAILED, CANCELLED
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    transaction = relationship("BillingTransaction", back_populates="payment_attempts")

# 23. Payment Records
class PaymentRecord(Base):
    __tablename__ = "payment_records"
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("billing_transactions.id"), nullable=False)
    payment_attempt_id = Column(Integer, ForeignKey("payment_attempts.id"), nullable=False)
    payment_reference = Column(String(100), unique=True, index=True, nullable=False)
    provider_tx_id = Column(String(100), nullable=False)
    signature = Column(String(255), nullable=False)
    verified_at = Column(DateTime, default=utc_now)
    amount_received = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="INR")

    transaction = relationship("BillingTransaction", back_populates="payment_records")

# 24. Receipts
class Receipt(Base):
    __tablename__ = "receipts"
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("billing_transactions.id"), nullable=False, unique=True)
    receipt_number = Column(String(100), unique=True, index=True, nullable=False)
    pdf_path = Column(String(500), nullable=True)
    qr_verification_token = Column(String(255), unique=True, nullable=False)
    generated_at = Column(DateTime, default=utc_now)

    transaction = relationship("BillingTransaction", back_populates="receipt")

# 25. Loyalty Accounts
class LoyaltyAccount(Base):
    __tablename__ = "loyalty_accounts"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, unique=True)
    points_balance = Column(Integer, default=0)
    tier = Column(String(50), default="BRONZE") # BRONZE, SILVER, GOLD
    last_activity = Column(DateTime, default=utc_now)

    customer = relationship("Customer", back_populates="loyalty_account")
    transactions = relationship("LoyaltyTransaction", back_populates="loyalty_account")

# 26. Loyalty Transactions
class LoyaltyTransaction(Base):
    __tablename__ = "loyalty_transactions"
    id = Column(Integer, primary_key=True, index=True)
    loyalty_account_id = Column(Integer, ForeignKey("loyalty_accounts.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("shopping_sessions.id"), nullable=True)
    points_change = Column(Integer, nullable=False)
    reason = Column(String(150), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    loyalty_account = relationship("LoyaltyAccount", back_populates="transactions")

# 27. Audit Logs
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=False)
    payload_json = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=utc_now, index=True)

    user = relationship("User", back_populates="audit_logs")

# 28. Device Health
class DeviceHealth(Base):
    __tablename__ = "device_health"
    id = Column(Integer, primary_key=True, index=True)
    trolley_id = Column(Integer, ForeignKey("trolley_devices.id"), nullable=False)
    battery_voltage = Column(Float, default=12.4)
    battery_percent = Column(Float, default=100.0)
    esp32_connected = Column(Boolean, default=True)
    hx711_status = Column(String(50), default="OK")
    imu_status = Column(String(50), default="OK")
    camera_status = Column(String(50), default="OK")
    wifi_rssi = Column(Integer, default=-55)
    recorded_at = Column(DateTime, default=utc_now, index=True)

    trolley = relationship("TrolleyDevice", back_populates="device_health_logs")
