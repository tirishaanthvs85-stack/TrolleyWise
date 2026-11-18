# TrolleyWise AI Model Setup & Computer Vision Pipeline

## 1. Computer Vision Architecture
TrolleyWise utilizes **Ultralytics YOLO** combined with centroid trajectory tracking to recognize retail products crossing the trolley basket perimeter.

Supported Core Classes:
- Class 0: `Milk` (SKU: `TW-MILK-001`, expected 515.0g ± 15g)
- Class 1: `Bread` (SKU: `TW-BREAD-002`, expected 405.0g ± 15g)
- Class 2: `Rice` (SKU: `TW-RICE-003`, expected 1020.0g ± 25g)
- Class 3: `Soap` (SKU: `TW-SOAP-004`, expected 128.0g ± 8g)
- Class 4: `Chocolate` (SKU: `TW-CHOC-005`, expected 52.0g ± 5g)

---

## 2. Model Initialization & Training Workflow

### Step 1: Initialize Custom Model Weights
To build the baseline model weights for the 5 catalogue classes:
```bash
python ai_models/train_or_export_yolo.py --action init
```
This generates `ai_models/weights/trolleywise_yolo.pt`.

### Step 2: Training on Custom Store Dataset
To fine-tune on captured camera frames using `data.yaml`:
```bash
python ai_models/train_or_export_yolo.py --action train --epochs 50
```

### Step 3: Jetson Edge Deployment (TensorRT / ONNX)
To optimize inference for NVIDIA Jetson Orin Nano / Orin NX:
```bash
python ai_models/train_or_export_yolo.py --action export --format onnx
```

---

## 3. Product Tracking & Ingress/Egress Analysis
The `AIProductRecognitionEngine` in `backend/app/services/ai_recognition.py`:
1. Detects bounding boxes with confidence scores.
2. Tracks centroids across consecutive frames.
3. Computes vertical/rim velocity vector:
   - Downward / Rim Crossing Inward $\rightarrow$ `INWARD` (Insertion candidate)
   - Upward / Rim Crossing Outward $\rightarrow$ `OUTWARD` (Removal candidate)
4. Enforces a 3-second cooldown window per SKU to prevent duplicate triggers.
