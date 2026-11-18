import os
from typing import List
from pydantic import BaseModel, Field

class Settings(BaseModel):
    PROJECT_NAME: str = "TrolleyWise AI Smart Shopping Cart"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "trolleywise-super-secret-production-key-change-in-prod-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./trolleywise.db")
    
    # Store / GST Configuration (Indian retail defaults)
    STORE_CODE: str = "TW-STORE-001"
    STORE_NAME: str = "TrolleyWise Hypermarket"
    STORE_ADDRESS: str = "Tech Corridor, Bengaluru, Karnataka 560100"
    STORE_GSTIN: str = "29AAAAA0000A1Z5"
    STORE_CURRENCY: str = "INR"
    STORE_CURRENCY_SYMBOL: str = "₹"
    DEFAULT_GST_RATE: float = 0.18 # 18% default (9% CGST + 9% SGST)
    
    # Multimodal Sensor Fusion Weights (Initial patent calibration parameters)
    WEIGHT_SCORE_VISUAL: float = 0.35
    WEIGHT_SCORE_WEIGHT: float = 0.30
    WEIGHT_SCORE_TEMPORAL: float = 0.15
    WEIGHT_SCORE_TRACKING: float = 0.10
    WEIGHT_SCORE_MOTION: float = 0.05
    WEIGHT_SCORE_CART_STATE: float = 0.05
    
    # Fusion Thresholds
    VERIFICATION_CONFIDENCE_THRESHOLD: float = 0.70
    UNCERTAINTY_THRESHOLD: float = 0.45
    WEIGHT_TOLERANCE_DEFAULT_PERCENT: float = 0.10 # +/- 10%
    WEIGHT_TOLERANCE_MIN_GRAMS: float = 5.0 # At least 5 grams tolerance
    IMU_MOTION_THRESHOLD_ACCEL: float = 0.35 # m/s^2 jitter threshold
    
    # AI / Computer Vision
    YOLO_MODEL_PATH: str = os.getenv("YOLO_MODEL_PATH", "ai_models/weights/trolleywise_yolo.pt")
    CAMERA_INPUT_SOURCES: List[str] = ["0", "1"] # Top camera, side camera
    CONFIDENCE_DETECTION_THRESHOLD: float = 0.50
    IOU_TRACKING_THRESHOLD: float = 0.45
    
    # Payment Provider Sandbox (Razorpay / UPI standard sandbox)
    PAYMENT_PROVIDER: str = "RAZORPAY_SANDBOX"
    PAYMENT_KEY_ID: str = os.getenv("PAYMENT_KEY_ID", "rzp_test_trolleywise_sandbox_key")
    PAYMENT_KEY_SECRET: str = os.getenv("PAYMENT_KEY_SECRET", "tw_secret_sandbox_signature_9921")
    PAYMENT_WEBHOOK_SECRET: str = os.getenv("PAYMENT_WEBHOOK_SECRET", "tw_whsec_secret_2026")
    UPI_VPA: str = "trolleywise@icici"
    
    # Receipt Directory
    RECEIPT_OUTPUT_DIR: str = os.getenv("RECEIPT_OUTPUT_DIR", "./generated_receipts")
    
    # Offline Cache / Sync
    OFFLINE_QUEUE_FILE: str = "./offline_sync_queue.json"

settings = Settings()
