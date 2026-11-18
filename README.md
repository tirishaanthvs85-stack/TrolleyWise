# TrolleyWise — AI-Powered Smart Shopping Cart System

[![GitHub Repo](https://img.shields.io/badge/GitHub-TrolleyWise-181717.svg?logo=github)](https://github.com/tirishaanthvs85-stack/TrolleyWise)
[![Live Demo](https://img.shields.io/badge/Deployment-Live%20Demo-brightgreen.svg)](https://tirishaanthvs85-stack.github.io/TrolleyWise/)
[![Tests](https://img.shields.io/badge/Tests-26%2F26%20Passing-brightgreen.svg)]()
[![Patent](https://img.shields.io/badge/Patent-Indian%20Filing-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-v0.143.0-teal.svg)]()
[![Python](https://img.shields.io/badge/Python-3.11-yellow.svg)]()

### 🌐 Live Deployment Links
- **Portal & Architecture Showcase:** [https://tirishaanthvs85-stack.github.io/TrolleyWise/](https://tirishaanthvs85-stack.github.io/TrolleyWise/)
- **Customer Touchscreen App:** [https://tirishaanthvs85-stack.github.io/TrolleyWise/touchscreen/](https://tirishaanthvs85-stack.github.io/TrolleyWise/touchscreen/)
- **Retailer Command Center:** [https://tirishaanthvs85-stack.github.io/TrolleyWise/retailer/](https://tirishaanthvs85-stack.github.io/TrolleyWise/retailer/)
- **GitHub Repository:** [https://github.com/tirishaanthvs85-stack/TrolleyWise](https://github.com/tirishaanthvs85-stack/TrolleyWise)

Production-oriented implementation of **TrolleyWise**, an intelligent shopping cart transaction system adhering to the filed Indian patent specification:
> **"TROLLEYWISE: AI-POWERED SMART SHOPPING CART WITH MULTIMODAL PRODUCT VERIFICATION, AUTOMATED BILLING AND ANOMALY DETECTION"**

The central operating paradigm is:
$$\text{PICK} \longrightarrow \text{DETECT} \longrightarrow \text{VERIFY} \longrightarrow \text{BILL} \longrightarrow \text{PAY} \longrightarrow \text{RECEIPT}$$

---

## 🚀 Key Features

1. **Multimodal Product Verification Engine:**
   - 6-modality sensor fusion: Visual AI (35%) + Weight Consistency (30%) + Temporal Alignment (15%) + Centroid Tracking Continuity (10%) + IMU Motion Stability (5%) + Digital Cart Consistency (5%).
   - Four Event States: `VERIFIED_INSERTION`, `VERIFIED_REMOVAL`, `UNCERTAIN_EVENT`, and `ANOMALY_EVENT`.
   - Only verified events modify confirmed billing.

2. **Computer Vision & Tracking Pipeline:**
   - Ultralytics YOLO object recognition with multi-camera support (top basket & side rim).
   - Multi-frame centroid tracking with ingress/egress trajectory analysis (`INWARD` vs `OUTWARD`).
   - Duplicate event suppression and occlusion handling.

3. **ESP32 Sensor Telemetry:**
   - 4x Wheatstone bridge load cells via HX711 with moving-average baseline filtering.
   - MPU-6050 6-DOF IMU acceleration and angular velocity readings to detect trolley motion and defer unstable weighing.
   - Production C++ firmware (`firmware/esp32_firmware.ino`) and live client (`hardware/esp32_client.py`).

4. **Live Automatic Billing Engine:**
   - Pure `Decimal` arithmetic for financial accuracy (zero floating-point errors).
   - Price, discount, and tax snapshotting to freeze catalogue rates for active sessions.
   - Promotional coupons, budget tracking with threshold alerts, and GST itemization (CGST + SGST).
   - Real-time updates pushed to customer screen via WebSockets.

5. **Customer Touchscreen & Retailer Command Center:**
   - **Customer Interface (`/touchscreen`):** Live cart, savings, budget progress, UPI QR modal, and anomaly confirmation dialogs.
   - **Retailer Dashboard (`/retailer`):** Real-time fleet health, stock levels, sales analytics, and audit logging.

6. **Payment & Tax Invoicing:**
   - Dynamic NPCI UPI QR code generation and sandbox payment flow.
   - Server-side cryptographic HMAC-SHA256 signature verification.
   - Official Indian GST-compliant PDF Tax Invoices generated via ReportLab with embedded authenticity QR codes.

---

## 🛠️ Quick Start

### 1. Run Backend Server
```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Access Web Interfaces
- **Customer Touchscreen Interface:** [http://localhost:8000/touchscreen](http://localhost:8000/touchscreen)
- **Retailer Admin Console:** [http://localhost:8000/retailer](http://localhost:8000/retailer)
- **Interactive Swagger Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Run Automated Tests
```bash
python -m pytest backend/tests/ -v
```

---

## 🐳 Docker Deployment
```bash
docker-compose up --build -d
```

---

## 📂 Project Structure
```
Trolleywise_org/
├── backend/
│   ├── app/
│   │   ├── api/endpoints/         # REST & WebSocket route handlers
│   │   ├── core/                  # Decimal financial utils, config, security, DB
│   │   ├── db/                    # 28 SQLAlchemy models and seed scripts
│   │   ├── schemas/               # Pydantic validation schemas
│   │   ├── services/              # Sensor fusion, AI vision, billing, payments, receipts
│   │   └── main.py                # FastAPI ASGI application entrypoint
│   └── tests/                     # 26 automated tests (100% passing)
├── frontend/
│   ├── customer_touchscreen/      # Modern touchscreen HTML5/JS app
│   └── retailer_dashboard/        # Retailer monitoring and inventory app
├── firmware/
│   └── esp32_firmware.ino         # Production ESP32 C++ firmware
├── hardware/
│   ├── esp32_client.py            # Real hardware serial/network client
│   └── esp32_simulator.py         # Explicitly labelled development testing simulator
├── ai_models/
│   ├── train_or_export_yolo.py    # YOLO training and TensorRT/ONNX export
│   └── weights/                   # Custom YOLO weights
├── legacy/                        # Preserved original prototype files
├── ARCHITECTURE.md                # System design & patent pipeline documentation
├── API_DOCUMENTATION.md           # REST & WebSocket endpoints reference
├── HARDWARE_INTEGRATION.md        # ESP32 pinouts and JSON telemetry protocol
├── AI_MODEL_SETUP.md              # Computer vision setup and model training
├── PAYMENT_SETUP.md               # Dynamic UPI QR & cryptographic verification
├── TEST_REPORT.md                 # Test matrix and verification results
└── docker-compose.yml             # Container orchestration
```
