# TrolleyWise API Documentation

Base URL: `http://localhost:8000/api`  
Interactive Swagger UI: `http://localhost:8000/docs`  
Interactive ReDoc UI: `http://localhost:8000/redoc`

---

## 1. Products
- `GET /api/products` — Retrieve all active products with price and weight specifications.
- `GET /api/products/{sku}` — Retrieve single product details by SKU.
- `POST /api/products` — Register a new catalogue product (requires price and weight).
- `PUT /api/products/{sku}` — Update product prices, weights, or metadata.

## 2. Trolley Devices & Hardware Telemetry
- `POST /api/trolley/register` — Register a smart cart hardware unit to a store.
- `GET /api/trolley/{device_uuid}/status` — Retrieve current trolley status, battery, and load cell weights.
- `POST /api/trolley/{device_uuid}/sensor-data` — Ingest real-time ESP32 load-cell and IMU telemetry.

## 3. Shopping Sessions & Cart Management
- `POST /api/sessions` — Start an active shopping session for a customer and cart.
- `GET /api/sessions/{session_id}` — Get session status and metadata.
- `GET /api/sessions/{session_id}/cart` — Get real-time digital cart contents and financial summary.
- `POST /api/sessions/{session_id}/events` — Record interaction events (e.g. barcode scan, help request).

## 4. Multimodal Verification & Anomaly Handling
- `POST /api/verification/evaluate` — Central patent evaluation endpoint. Submits visual recognition and sensor telemetry; automatically updates cart on verified events.
- `GET /api/verification/events` — Retrieve historical verification log with scores.
- `GET /api/anomalies` — List active unresolved discrepancies and alarms.
- `POST /api/anomalies/{anomaly_id}/resolve` — Resolve an anomaly via customer confirmation or staff override.

## 5. Billing Engine
- `GET /api/billing/{session_id}` — Retrieve the current recalculation of the bill.
- `POST /api/billing/{session_id}/recalculate` — Recalculate bill with optional promo/coupon code.
- `POST /api/billing/{session_id}/checkout` — Freeze digital cart and initiate payment order.

## 6. Payment Integration
- `POST /api/payments/create-order` — Create payment gateway order with idempotency protection.
- `POST /api/payments/verify` — Server-side cryptographic signature verification.
- `POST /api/payments/webhook` — Gateway asynchronous signed webhook receiver.

## 7. Electronic Receipts & Inventory
- `GET /api/receipts/{transaction_id}` — Get receipt metadata and verification token.
- `GET /api/receipts/{transaction_id}/pdf` — Stream and download the ReportLab PDF Tax Invoice.
- `GET /api/inventory` — Get store stock levels, thresholds, and replenishment status.
- `POST /api/inventory/synchronize` — Replay and sync offline queued events with central ledger.

## 8. WebSockets
- `WS /ws/live/{channel_id}` — Real-time event stream for customer touchscreen and retailer console.
