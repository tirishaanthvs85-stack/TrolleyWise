"""
TrolleyWise AI Product Recognition & Multi-Camera Tracking Engine
Implements Section 3 of Patent Specification:
- Multi-camera frame ingestion (Top basket camera & side rim camera)
- YOLO product detection and classification
- Multi-frame object tracking and centroid trajectory calculation
- Entry/Exit movement vector analysis (INWARD vs OUTWARD)
- Occlusion resistance and duplicate trigger suppression
- Catalogue SKU association
"""

import os
import cv2
import time
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from ultralytics import YOLO
from backend.app.core.config import settings

CLASS_TO_SKU = {
    0: "TW-MILK-001",
    1: "TW-BREAD-002",
    2: "TW-RICE-003",
    3: "TW-SOAP-004",
    4: "TW-CHOC-005",
    "Milk": "TW-MILK-001",
    "Bread": "TW-BREAD-002",
    "Rice": "TW-RICE-003",
    "Soap": "TW-SOAP-004",
    "Chocolate": "TW-CHOC-005"
}

class TrackedProduct:
    def __init__(self, track_id: int, class_id: int, class_name: str, bbox: List[float], confidence: float):
        self.track_id = track_id
        self.class_id = class_id
        self.class_name = class_name
        self.sku = CLASS_TO_SKU.get(class_id, CLASS_TO_SKU.get(class_name, f"TW-PROD-{class_id}"))
        self.bbox_history = [bbox]
        self.confidence_history = [confidence]
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.frames_tracked = 1
        self.disappeared_frames = 0
        self.direction = "UNCERTAIN" # INWARD, OUTWARD, UNCERTAIN

    @property
    def current_bbox(self) -> List[float]:
        return self.bbox_history[-1]

    @property
    def avg_confidence(self) -> float:
        return float(np.mean(self.confidence_history[-5:]))

    @property
    def centroid(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.current_bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def update(self, bbox: List[float], confidence: float, frame_height: int = 480):
        self.bbox_history.append(bbox)
        self.confidence_history.append(confidence)
        self.last_seen = time.time()
        self.frames_tracked += 1
        self.disappeared_frames = 0

        # Calculate movement vector (Y-axis transition: from upper entrance toward basket floor)
        if len(self.bbox_history) >= 2:
            prev_y = (self.bbox_history[-2][1] + self.bbox_history[-2][3]) / 2.0
            curr_y = (bbox[1] + bbox[3]) / 2.0
            delta_y = curr_y - prev_y
            
            # Entering cart: downward movement in top-view or crossing rim ROI
            if delta_y > 4.0:
                self.direction = "INWARD"
            elif delta_y < -4.0:
                self.direction = "OUTWARD"

class AIProductRecognitionEngine:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.model_path = settings.YOLO_MODEL_PATH
        self.model = self._load_model()
        self.trackers: Dict[int, TrackedProduct] = {}
        self.next_track_id = 1
        self.event_cooldowns: Dict[str, float] = {} # Key: "sku_direction", Value: timestamp
        self._initialized = True

    def _load_model(self) -> Optional[YOLO]:
        """Loads actual YOLO model weights. If not yet created, initializes them."""
        try:
            if not os.path.exists(self.model_path):
                from ai_models.train_or_export_yolo import init_default_model
                init_default_model(self.model_path)
            print(f"[AI Engine] Loading YOLO weights from: {self.model_path}")
            model = YOLO(self.model_path)
            return model
        except Exception as e:
            print(f"[AI Engine] Warning loading YOLO: {e}. Model will run in fallback inspection mode.")
            return None

    def process_frame(
        self,
        frame: np.ndarray,
        camera_id: str = "CAM_TOP",
        confidence_threshold: float = 0.40
    ) -> Dict[str, Any]:
        """
        Runs real YOLO inference on camera frame, updates multi-object trackers,
        and determines candidate product insertion/removal events.
        """
        h, w = frame.shape[:2]
        detections = []
        
        if self.model is not None:
            try:
                # Actual YOLO inference
                results = self.model.predict(
                    source=frame,
                    conf=confidence_threshold,
                    verbose=False,
                    imgsz=640
                )
                if len(results) > 0 and results[0].boxes is not None:
                    boxes = results[0].boxes
                    for i in range(len(boxes)):
                        xyxy = boxes.xyxy[i].cpu().numpy().tolist()
                        conf = float(boxes.conf[i].cpu().item())
                        cls_id = int(boxes.cls[i].cpu().item())
                        cls_name = self.model.names.get(cls_id, str(cls_id))
                        sku = CLASS_TO_SKU.get(cls_id, CLASS_TO_SKU.get(cls_name, f"TW-PROD-{cls_id}"))
                        detections.append({
                            "bbox": xyxy,
                            "confidence": conf,
                            "class_id": cls_id,
                            "class_name": cls_name,
                            "sku": sku
                        })
            except Exception as ex:
                print(f"[AI Engine] Model prediction error: {ex}")

        # Update multi-frame trackers
        matched_tracker_ids = set()
        active_events = []

        for det in detections:
            bbox = det["bbox"]
            conf = det["confidence"]
            sku = det["sku"]
            cx, cy = (bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0

            # Find matching existing tracker via centroid distance
            best_match_id = None
            min_dist = float("inf")
            for t_id, tracker in self.trackers.items():
                if tracker.sku == sku:
                    tcx, tcy = tracker.centroid
                    dist = np.hypot(cx - tcx, cy - tcy)
                    if dist < 80.0 and dist < min_dist:
                        min_dist = dist
                        best_match_id = t_id

            if best_match_id is not None:
                tracker = self.trackers[best_match_id]
                tracker.update(bbox, conf, frame_height=h)
                matched_tracker_ids.add(best_match_id)
            else:
                # New tracked product entering frame
                new_id = self.next_track_id
                self.next_track_id += 1
                tracker = TrackedProduct(new_id, det["class_id"], det["class_name"], bbox, conf)
                self.trackers[new_id] = tracker
                matched_tracker_ids.add(new_id)

            # Evaluate candidate event
            cooldown_key = f"{tracker.sku}_{tracker.direction}"
            now = time.time()
            if tracker.frames_tracked >= 2 and tracker.direction in ["INWARD", "OUTWARD"]:
                last_event_time = self.event_cooldowns.get(cooldown_key, 0.0)
                if now - last_event_time > 3.0: # 3 second suppression cooldown
                    self.event_cooldowns[cooldown_key] = now
                    active_events.append({
                        "tracker_id": tracker.track_id,
                        "sku": tracker.sku,
                        "class_name": tracker.class_name,
                        "direction": tracker.direction,
                        "confidence": tracker.avg_confidence,
                        "bbox": tracker.current_bbox,
                        "timestamp": now,
                        "camera_id": camera_id
                    })

        # Age out disappeared trackers (occlusion window: 15 frames)
        for t_id in list(self.trackers.keys()):
            if t_id not in matched_tracker_ids:
                self.trackers[t_id].disappeared_frames += 1
                if self.trackers[t_id].disappeared_frames > 15:
                    del self.trackers[t_id]

        return {
            "camera_id": camera_id,
            "raw_detections": detections,
            "tracked_objects_count": len(self.trackers),
            "candidate_events": active_events
        }

    def annotate_frame(self, frame: np.ndarray, vision_result: Dict[str, Any]) -> np.ndarray:
        """Draws bounding boxes, SKU tags, and movement vectors on camera frame."""
        annotated = frame.copy()
        for det in vision_result.get("raw_detections", []):
            x1, y1, x2, y2 = map(int, det["bbox"])
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"{det['class_name']} ({det['sku']}) {det['confidence']:.2f}"
            cv2.putText(annotated, label, (x1, max(y1 - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return annotated

# Global AI Engine singleton
ai_recognition_engine = AIProductRecognitionEngine()
