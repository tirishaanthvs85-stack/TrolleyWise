# TrolleyWise System Architecture

## Patent Reference
**Patent Title:** TROLLEYWISE: AI-POWERED SMART SHOPPING CART WITH MULTIMODAL PRODUCT VERIFICATION, AUTOMATED BILLING AND ANOMALY DETECTION  
**Indian Patent Filing:** In-flight retail automation specification  

---

## 1. High-Level Pipeline Architecture

The system connects physical product movement with verified digital billing across an end-to-end processing pipeline:

```
RGB Cameras (Top Basket & Side Rim)
    ↓
Computer Vision Product Recognition (YOLO + Multi-object Tracking)
    ↓
Movement Direction & SKU Mapping (INWARD vs OUTWARD)
    ↓
ESP32 Sensor Telemetry (4x Load Cells via HX711 + 6-DOF IMU)
    ↓
Load-Cell Filtering & Weight Baseline Tracking (ΔW Transition)
    ↓
IMU Motion Stability Check (Stationary vs In-Motion)
    ↓
Multimodal Sensor Fusion Engine
    ├── Visual Confidence (35%)
    ├── Weight Consistency (30%)
    ├── Temporal Alignment (15%)
    ├── Tracking Continuity (10%)
    ├── Motion Stability (5%)
    └── Cart-State Consistency (5%)
    ↓
Product Event State Evaluation
    ├── VERIFIED_INSERTION   → Commit to digital cart & live billing
    ├── VERIFIED_REMOVAL     → Decrement from digital cart & update bill
    ├── UNCERTAIN_EVENT      → Withhold from bill, prompt customer confirmation
    └── ANOMALY_EVENT        → Pause transition, flag audit incident, notify staff
    ↓
Automatic Decimal Billing Engine (Price Snapshotting + GST Invoicing)
    ↓
Customer Touchscreen (Live WebSockets, Budget Tracking, Anomaly Modal)
    ↓
Checkout & Dynamic UPI QR Payment Order
    ↓
Server-Side Authenticated Signature Verification
    ↓
Electronic Tax Receipt (ReportLab PDF + Verification QR)
    ↓
Atomic Retailer Inventory Synchronization (Guaranteed exactly once)
```

---

## 2. Multimodal Fusion Engine Formulation

The central intelligence correlates visual data, weight dynamics, time alignment, and motion stability:

$$\text{Confidence} = w_v \cdot S_{\text{visual}} + w_w \cdot S_{\text{weight}} + w_t \cdot S_{\text{temporal}} + w_k \cdot S_{\text{tracking}} + w_m \cdot S_{\text{motion}} + w_c \cdot S_{\text{cart}}$$

Where default calibrated weights are:
- $w_v = 0.35$ (Visual AI Confidence)
- $w_w = 0.30$ (Weight Consistency with Catalogue Expected Weight)
- $w_t = 0.15$ (Temporal Synchronization Window $\le 1.5$s)
- $w_k = 0.10$ (Multi-Frame Centroid Tracking Continuity)
- $w_m = 0.05$ (IMU Motion Stability, $a_{\text{dynamic}} \le 0.35\text{ m/s}^2$)
- $w_c = 0.05$ (Cart-State Validity: removal requires item in cart)

### Verification Thresholds:
- **$\text{Confidence} \ge 0.70$ AND $S_{\text{visual}} \ge 0.60$**: `VERIFIED_INSERTION` or `VERIFIED_REMOVAL`
- **$0.45 \le \text{Confidence} < 0.70$**: `UNCERTAIN_EVENT` (prompt customer confirmation)
- **$\text{Confidence} < 0.45$ OR Severe Mismatch**: `ANOMALY_EVENT`

---

## 3. Database Architecture (28 Normalized Entities)

All entities are implemented via SQLAlchemy 2 with foreign keys, indexes, and constraints:
1. `users` — System accounts, passwords, roles (`CUSTOMER`, `CASHIER`, `STORE_MANAGER`, `ADMIN`).
2. `customers` — Customer profile, phone number, preference constraints.
3. `retailers` — Enterprise retailer identity and GST registration.
4. `stores` — Physical store branches, locations, and default tax configurations.
5. `trolley_devices` — Physical smart carts, MAC/IP, firmware, battery, heartbeat.
6. `product_categories` — Product categories, HSN codes, default GST rates.
7. `product_catalog` — Master catalogue with SKUs, barcodes, brands, images.
8. `product_prices` — Time-stamped store prices and active price records.
9. `product_weights` — Expected weight in grams and tolerance margins.
10. `inventory` — Real-time store stock, reserved quantities, replenishment thresholds.
11. `promotions` — Store marketing campaigns, coupon codes, valid windows.
12. `discount_rules` — Minimum basket values, discount percentages, caps.
13. `shopping_sessions` — Active and completed customer shopping trips.
14. `digital_carts` — Versioned digital cart containers.
15. `cart_items` — Itemized cart entries with frozen unit price snapshots.
16. `sensor_readings` — Raw and filtered load-cell grams and 6-DOF IMU vectors.
17. `camera_events` — Captured video frames and ingress/egress trajectories.
18. `product_detections` — YOLO bounding boxes, class IDs, and confidences.
19. `verification_events` — Multimodal fusion scores, status, and audit records.
20. `anomaly_events` — Security and discrepancy incident tracking with severity.
21. `billing_transactions` — Official financial transactions with GST breakdown.
22. `payment_attempts` — Gateway order IDs, idempotency keys, and statuses.
23. `payment_records` — Confirmed payments with cryptographic gateway signatures.
24. `receipts` — Electronic invoices, PDF documents, and verification tokens.
25. `loyalty_accounts` — Customer reward points and tiers (Bronze, Silver, Gold).
26. `loyalty_transactions` — Accrual and redemption histories.
27. `audit_logs` — Tamper-evident ledger of all critical store actions.
28. `device_health` — Hardware diagnostics, voltages, and peripheral statuses.

---

## 4. Financial Calculation Engine

To prevent floating-point inaccuracies, the billing system relies entirely on Python's `Decimal` type with `ROUND_HALF_UP` precision:

$$\text{Line Subtotal} = \text{Quantity} \times \text{Unit Price Snapshot}$$
$$\text{Line Discount} = \text{Quantity} \times \text{Unit Discount Snapshot}$$
$$\text{Taxable Amount} = \text{Line Subtotal} - \text{Eligible Discount}$$
$$\text{CGST} = \text{Taxable Amount} \times \left(\frac{\text{GST Rate}}{2}\right)$$
$$\text{SGST} = \text{Taxable Amount} \times \left(\frac{\text{GST Rate}}{2}\right)$$
$$\text{Final Total} = \sum \text{Taxable Amount} + \sum \text{Taxes}$$
