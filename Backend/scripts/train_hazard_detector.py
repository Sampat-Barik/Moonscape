"""Train, evaluate, and export the Moonscape Optical Lunar Hazard Detector (YOLOv8n).

Finetunes pretrained weights on the geographically partitioned lunar South Pole
orbital dataset (craters and boulders), evaluates on the unseen held-out test set,
exports to ONNX, and writes comprehensive metadata.
"""

import json
import os
from pathlib import Path
import shutil
import time

import numpy as np
import torch
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = DATA_DIR / "models"
DATASET_YAML = DATA_DIR / "hazard_dataset" / "lunar_hazard.yaml"
BASE_WEIGHTS = MODELS_DIR / "candidate_yolov8n_hazard.pt"
TARGET_PT = MODELS_DIR / "luna_hazard_yolov8n.pt"
TARGET_ONNX = MODELS_DIR / "luna_hazard_yolov8n.onnx"
TARGET_META = MODELS_DIR / "luna_hazard_yolov8n.meta.json"


def train_and_evaluate():
    print("=" * 70)
    print("MOONSCAPE OPTICAL HAZARD DETECTOR TRAINING PIPELINE")
    print("=" * 70)
    print(f"Dataset YAML: {DATASET_YAML}")
    print(f"Base Weights: {BASE_WEIGHTS}")

    assert DATASET_YAML.exists(), f"Dataset config missing: {DATASET_YAML}"
    assert BASE_WEIGHTS.exists(), f"Base weights missing: {BASE_WEIGHTS}"

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Initialize YOLOv8n detector with lunar base weights
    print("\n1. Initializing YOLOv8n model...")
    model = YOLO(str(BASE_WEIGHTS))

    # 2. Train with conservative augmentations suited for lunar polar orbital scenes
    print("\n2. Starting fine-tuning (15 epochs, batch=8, imgsz=640)...")
    runs_dir = DATA_DIR / "runs_hazard"
    if runs_dir.exists():
        shutil.rmtree(runs_dir, ignore_errors=True)

    t0 = time.time()
    train_results = model.train(
        data=str(DATASET_YAML),
        epochs=15,
        batch=8,
        imgsz=640,
        device="cpu",
        workers=2,
        project=str(runs_dir),
        name="luna_hazard_run",
        exist_ok=True,
        # Lunar orbital conservative augmentations (grayscale invariance, rotation invariance)
        hsv_h=0.015,
        hsv_s=0.0,
        hsv_v=0.1,
        degrees=15.0,
        translate=0.1,
        scale=0.1,
        fliplr=0.5,
        flipud=0.5,
        mosaic=0.5,
        verbose=True,
    )
    train_time = round(time.time() - t0, 2)
    print(f"\nTraining completed in {train_time} seconds.")

    # 3. Save best weights
    best_weights = runs_dir / "luna_hazard_run" / "weights" / "best.pt"
    if not best_weights.exists():
        best_weights = runs_dir / "luna_hazard_run" / "weights" / "last.pt"

    shutil.copyfile(str(best_weights), str(TARGET_PT))
    print(f"Saved fine-tuned PyTorch checkpoint to: {TARGET_PT}")

    # 4. Load best trained model for formal validation and held-out test evaluation
    best_model = YOLO(str(TARGET_PT))

    print("\n3. Evaluating on Validation Split (Malapert Mountain & Haworth Rim)...")
    val_results = best_model.val(
        data=str(DATASET_YAML),
        split="val",
        batch=8,
        imgsz=640,
        device="cpu",
        verbose=False,
    )

    print("\n4. Evaluating on Unseen Held-Out Test Split (de Gerlache Crater Rim 1 & 2)...")
    test_results = best_model.val(
        data=str(DATASET_YAML),
        split="test",
        batch=8,
        imgsz=640,
        device="cpu",
        verbose=False,
    )

    # Extract metrics helper
    def extract_metrics(res):
        mp = float(res.box.mp)
        mr = float(res.box.mr)
        map50 = float(res.box.map50)
        map50_95 = float(res.box.map)
        f1 = (2 * mp * mr / (mp + mr)) if (mp + mr) > 0 else 0.0

        # Per-class metrics
        p_c = res.box.p
        r_c = res.box.r
        map50_c = res.box.ap50
        map50_95_c = res.box.ap

        crater_p = float(p_c[0]) if len(p_c) > 0 else 0.0
        crater_r = float(r_c[0]) if len(r_c) > 0 else 0.0
        crater_f1 = (2 * crater_p * crater_r / (crater_p + crater_r)) if (crater_p + crater_r) > 0 else 0.0
        crater_map50 = float(map50_c[0]) if len(map50_c) > 0 else 0.0
        crater_map50_95 = float(map50_95_c[0]) if len(map50_95_c) > 0 else 0.0

        boulder_p = float(p_c[1]) if len(p_c) > 1 else 0.0
        boulder_r = float(r_c[1]) if len(r_c) > 1 else 0.0
        boulder_f1 = (2 * boulder_p * boulder_r / (boulder_p + boulder_r)) if (boulder_p + boulder_r) > 0 else 0.0
        boulder_map50 = float(map50_c[1]) if len(map50_c) > 1 else 0.0
        boulder_map50_95 = float(map50_95_c[1]) if len(map50_95_c) > 1 else 0.0

        return {
            "overall": {
                "precision": round(mp, 4),
                "recall": round(mr, 4),
                "f1_score": round(f1, 4),
                "mAP50": round(map50, 4),
                "mAP50_95": round(map50_95, 4),
            },
            "crater": {
                "precision": round(crater_p, 4),
                "recall": round(crater_r, 4),
                "f1_score": round(crater_f1, 4),
                "mAP50": round(crater_map50, 4),
                "mAP50_95": round(crater_map50_95, 4),
            },
            "boulder": {
                "precision": round(boulder_p, 4),
                "recall": round(boulder_r, 4),
                "f1_score": round(boulder_f1, 4),
                "mAP50": round(boulder_map50, 4),
                "mAP50_95": round(boulder_map50_95, 4),
            },
        }

    val_metrics = extract_metrics(val_results)
    test_metrics = extract_metrics(test_results)

    print("\n--- VALIDATION METRICS ---")
    print(json.dumps(val_metrics, indent=2))
    print("\n--- HELD-OUT TEST METRICS ---")
    print(json.dumps(test_metrics, indent=2))

    # 5. Export to ONNX
    print("\n5. Exporting model to ONNX format (opset 18, 640x640)...")
    exported_path = best_model.export(
        format="onnx",
        imgsz=640,
        opset=18,
        dynamic=False,
        simplify=False,
    )
    if exported_path and Path(exported_path).exists():
        if Path(exported_path).resolve() != TARGET_ONNX.resolve():
            shutil.copyfile(str(exported_path), str(TARGET_ONNX))
        print(f"Exported ONNX model to: {TARGET_ONNX}")

    # Benchmark CPU inference latency
    print("\n6. Benchmarking inference latency...")
    dummy_input = torch.zeros((1, 3, 640, 640), dtype=torch.float32)
    # Warmup
    for _ in range(5):
        _ = best_model(dummy_input, verbose=False)

    latencies = []
    for _ in range(20):
        t_start = time.perf_counter()
        _ = best_model(dummy_input, verbose=False)
        latencies.append((time.perf_counter() - t_start) * 1000.0)

    mean_latency_ms = round(float(np.mean(latencies)), 2)
    p95_latency_ms = round(float(np.percentile(latencies, 95)), 2)
    print(f"Inference Latency: Mean = {mean_latency_ms} ms, P95 = {p95_latency_ms} ms")

    # 6. Generate comprehensive model metadata
    metadata = {
        "model_name": "Moonscape Lunar South Pole Optical Hazard Detector",
        "version": "1.0.0",
        "architecture": "YOLOv8n-Detection",
        "parameters": "3.0M",
        "input_shape": [1, 3, 640, 640],
        "input_channels": 3,
        "input_normalization": "pixel values scaled to [0.0, 1.0]",
        "classes": ["crater", "boulder"],
        "class_id_mapping": {0: "crater", 1: "boulder"},
        "training": {
            "base_checkpoint": "candidate_yolov8n_hazard.pt",
            "epochs": 15,
            "batch_size": 8,
            "image_size": 640,
            "optimizer": "AdamW",
            "augmentations": {
                "hsv_h": 0.015,
                "hsv_s": 0.0,
                "hsv_v": 0.1,
                "rotation_deg": 15.0,
                "fliplr": 0.5,
                "flipud": 0.5,
                "mosaic": 0.5,
            },
            "training_time_seconds": train_time,
        },
        "dataset": {
            "source": "LROC NAC (Narrow Angle Camera) / Chandrayaan-2 OHRC polar orbital frames",
            "total_tiles": 80,
            "total_annotated_instances": 4136,
            "train_samples": 40,
            "val_samples": 20,
            "test_samples": 20,
            "train_regions": "Shackleton Connecting Ridge & Bench (Artemis Site 01)",
            "val_regions": "Malapert Mountain Summit Massif & Haworth Rim (Artemis Site 02)",
            "test_regions": "de Gerlache Crater Rim 1 & 2 (Candidate Artemis Sites 03 & 04 - Zero Geographic Leakage)",
            "spatial_resolution_mpp_range": [1.2, 1.8],
            "solar_incidence_deg_range": [78.0, 84.5],
        },
        "evaluation_metrics": {
            "validation_split": val_metrics,
            "held_out_test_split": test_metrics,
        },
        "performance_benchmarks": {
            "hardware": "AMD Ryzen 9 894HX (CPU Execution)",
            "mean_latency_ms": mean_latency_ms,
            "p95_latency_ms": p95_latency_ms,
            "fps": round(1000.0 / mean_latency_ms, 1) if mean_latency_ms > 0 else 0,
        },
        "operational_limitations": {
            "apollo_domain_warning": (
                "Apollo surface photography (sun elevation > 15 deg, astronaut eye-level view) "
                "is invalid for orbital nadir crater/boulder mapping. This model was trained and evaluated "
                "strictly on high-resolution polar orbital imagery with grazing sun angles (solar incidence 78°-84.5°)."
            ),
            "permanently_shadowed_regions": (
                "Optical detection fails in zero-illumination Permanently Shadowed Regions (PSRs). "
                "DEM LiDAR roughness, slope, and radar backscatter must be used inside PSRs."
            ),
            "safety_critical_disclaimer": (
                "Intended for preliminary candidate site screening and mission planning only. "
                "NOT certified for autonomous real-time landing descent or human-rated hazard avoidance."
            ),
        },
    }

    with open(TARGET_META, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSaved metadata JSON to: {TARGET_META}")
    print("\n" + "=" * 70)
    print("TRAINING AND EVALUATION COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    train_and_evaluate()
