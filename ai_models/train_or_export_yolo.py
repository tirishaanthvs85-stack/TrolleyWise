"""
TrolleyWise AI - Computer Vision YOLO Training & Jetson TensorRT Export Script
Used to train, validate and export custom YOLO models for smart shopping cart recognition.
Classes:
  0: Milk (TW-MILK-001)
  1: Bread (TW-BREAD-002)
  2: Rice (TW-RICE-003)
  3: Soap (TW-SOAP-004)
  4: Chocolate (TW-CHOC-005)
"""

import os
import argparse
import torch
from ultralytics import YOLO

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_WEIGHTS = os.path.join(MODEL_DIR, "weights", "trolleywise_yolo.pt")

CLASS_NAMES = {
    0: "Milk",
    1: "Bread",
    2: "Rice",
    3: "Soap",
    4: "Chocolate"
}

def init_default_model(output_path=DEFAULT_WEIGHTS):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print(f"Initializing custom TrolleyWise YOLO model at: {output_path}")
    base_model = YOLO("yolov8n.yaml")
    base_model.model.names = CLASS_NAMES
    torch.save({
        "model": base_model.model,
        "names": CLASS_NAMES,
        "version": "2.0.0-trolleywise"
    }, output_path)
    print(f"Successfully generated initial weights for classes: {CLASS_NAMES}")

def train_model(data_yaml="data.yaml", epochs=50, imgsz=640, output_dir="runs/train"):
    print(f"Starting YOLO training with dataset configuration: {data_yaml} for {epochs} epochs...")
    model = YOLO(DEFAULT_WEIGHTS if os.path.exists(DEFAULT_WEIGHTS) else "yolov8n.pt")
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        project=output_dir,
        name="trolleywise_run"
    )
    print("Training completed. Results:", results)
    best_weights = os.path.join(output_dir, "trolleywise_run", "weights", "best.pt")
    if os.path.exists(best_weights):
        import shutil
        shutil.copy(best_weights, DEFAULT_WEIGHTS)
        print(f"Copied best model weights to {DEFAULT_WEIGHTS}")

def export_for_jetson(format="onnx"):
    """Exports model for Jetson Orin Nano / NX edge acceleration (TensorRT / ONNX)."""
    if not os.path.exists(DEFAULT_WEIGHTS):
        init_default_model(DEFAULT_WEIGHTS)
    print(f"Exporting model {DEFAULT_WEIGHTS} to {format} format for Jetson edge inference...")
    model = YOLO(DEFAULT_WEIGHTS)
    exported = model.export(format=format, dynamic=True)
    print(f"Model exported successfully: {exported}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TrolleyWise YOLO Model Training & Export")
    parser.add_argument("--action", choices=["init", "train", "export"], default="init")
    parser.add_argument("--format", choices=["onnx", "engine"], default="onnx")
    parser.add_argument("--epochs", type=int, default=50)
    args = parser.parse_args()

    if args.action == "init":
        init_default_model()
    elif args.action == "train":
        train_model(epochs=args.epochs)
    elif args.action == "export":
        export_for_jetson(format=args.format)
