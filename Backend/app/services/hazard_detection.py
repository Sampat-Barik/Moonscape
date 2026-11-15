"""Lunar Hazard Detection & ML Inference Service.

Handles model loading, image decoding, input validation, preprocessing,
inference execution, confidence thresholding, metric spatial calibration,
and domain gap validation for crater and rock hazard detection.
"""

import base64
import io
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image, UnidentifiedImageError

from app.config.hazard_settings import hazard_settings
from app.core.logging import logger
from app.schemas.hazard import (
    BoundingBox,
    DetectionItem,
    HazardPredictRequest,
    HazardPredictResponse,
)

APOLLO_DOMAIN_LIMITATION = (
    "CRITICAL SCIENTIFIC NOTICE: Models trained exclusively on Apollo surface photography "
    "(equatorial/mid-latitude, sun elevation > 15 deg) are INVALIDATED for orbital South Pole "
    "landing corridors due to extreme grazing-angle illumination (< 1.5 deg), severe elongated "
    "shadows, permanently shadowed regions (PSRs), and polar stereographic distortion. "
    "Current status: Ground-truth validation required against high-resolution LROC NAC and LOLA polar datasets."
)


class HazardDetectionService:
    """Manages deep-learning and computer vision hazard detection inference for lunar landing sites."""

    def __init__(self) -> None:
        self._model: Optional[Any] = None
        self._model_type: Optional[str] = None  # "onnx", "torch", "custom", or None
        self._metadata: Dict[str, Any] = {}
        self._is_configured: bool = False
        self._custom_inference_fn: Optional[Callable[[np.ndarray], Any]] = None

    def load_model(
        self,
        model_path: Optional[Union[str, Path]] = None,
        metadata_path: Optional[Union[str, Path]] = None,
    ) -> bool:
        """Loads machine learning model into memory once at application startup.

        Gracefully detects whether a model file exists. If not found or if deep learning
        libraries are not installed, sets is_available() = False and does not crash.
        """
        resolved_model_path: Optional[Path] = None

        if model_path:
            p = Path(model_path)
            if p.exists():
                resolved_model_path = p
        elif hazard_settings.HAZARD_MODEL_PATH and Path(hazard_settings.HAZARD_MODEL_PATH).exists():
            resolved_model_path = Path(hazard_settings.HAZARD_MODEL_PATH)
        else:
            # Scan models directory for candidate weights in priority order
            model_dir = hazard_settings.MODEL_DIR
            if model_dir.exists():
                preferred_weights = [
                    "luna_hazard_yolov8n.pt",
                    "luna_hazard_yolov8n.onnx",
                    "candidate_yolov8n_hazard.pt",
                    "candidate_yolov8n_hazard.onnx",
                ]
                for w_name in preferred_weights:
                    cand = model_dir / w_name
                    if cand.exists():
                        resolved_model_path = cand
                        break
                if not resolved_model_path:
                    candidates = list(model_dir.glob("*.onnx")) + list(model_dir.glob("*.pt")) + list(model_dir.glob("*.pth"))
                    if candidates:
                        resolved_model_path = candidates[0]

        # Load metadata if present
        meta_p: Optional[Path] = None
        if metadata_path and Path(metadata_path).exists():
            meta_p = Path(metadata_path)
        elif hazard_settings.HAZARD_METADATA_PATH and Path(hazard_settings.HAZARD_METADATA_PATH).exists():
            meta_p = Path(hazard_settings.HAZARD_METADATA_PATH)
        elif hazard_settings.MODEL_DIR.exists():
            preferred_metas = [
                "luna_hazard_yolov8n.meta.json",
                "candidate_yolov8n_hazard.meta.json",
                "model_metadata.json",
            ]
            for m_name in preferred_metas:
                cand_meta = hazard_settings.MODEL_DIR / m_name
                if cand_meta.exists():
                    meta_p = cand_meta
                    break

        if meta_p and meta_p.exists():
            try:
                with open(meta_p, "r", encoding="utf-8") as f:
                    self._metadata = json.load(f)
            except Exception as e:
                logger.warning("Failed to load model metadata from %s: %s", meta_p, str(e))
                self._metadata = {}

        if not resolved_model_path or not resolved_model_path.exists():
            logger.info("Hazard detection model not configured. Inference service is currently offline.")
            self._model = None
            self._model_type = None
            self._is_configured = False
            return False

        # Attempt to load model based on file format
        ext = resolved_model_path.suffix.lower()
        try:
            # Check if model can be loaded with Ultralytics YOLO
            if "yolo" in resolved_model_path.name.lower() or ext in [".pt", ".onnx"]:
                try:
                    from ultralytics import YOLO

                    self._model = YOLO(str(resolved_model_path))
                    self._model_type = "yolo"
                    self._is_configured = True
                    logger.info("Loaded YOLO hazard detection model from %s", resolved_model_path)
                    return True
                except Exception as yolo_err:
                    logger.warning("Ultralytics YOLO load failed: %s. Falling back to onnxruntime/torch.", yolo_err)

            if ext == ".onnx":
                try:
                    import onnxruntime as ort

                    # Configure hardware execution providers (CUDA on RTX 5070 if available, else CPU)
                    providers = ["CPUExecutionProvider"]
                    if hazard_settings.PREFERRED_DEVICE == "cuda":
                        available_providers = ort.get_available_providers()
                        if "CUDAExecutionProvider" in available_providers:
                            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]

                    self._model = ort.InferenceSession(str(resolved_model_path), providers=providers)
                    self._model_type = "onnx"
                    self._is_configured = True
                    logger.info("Loaded ONNX hazard detection model from %s with providers %s", resolved_model_path, providers)
                    return True
                except ImportError:
                    logger.warning("onnxruntime is not installed. Unable to load ONNX model at %s", resolved_model_path)
                    self._is_configured = False
                    return False

            elif ext in [".pt", ".pth"]:
                try:
                    import torch

                    device = "cuda" if (torch.cuda.is_available() and hazard_settings.PREFERRED_DEVICE == "cuda") else "cpu"
                    try:
                        # Attempt TorchScript load first
                        self._model = torch.jit.load(str(resolved_model_path), map_location=device)
                    except Exception:
                        # Fallback to weights dictionary or standard torch.load
                        self._model = torch.load(str(resolved_model_path), map_location=device, weights_only=False)

                    if hasattr(self._model, "eval"):
                        self._model.eval()

                    self._model_type = "torch"
                    self._is_configured = True
                    logger.info("Loaded PyTorch hazard detection model from %s on device %s", resolved_model_path, device)
                    return True
                except ImportError:
                    logger.warning("torch is not installed. Unable to load PyTorch model at %s", resolved_model_path)
                    self._is_configured = False
                    return False
            else:
                logger.warning("Unsupported model format '%s' at %s", ext, resolved_model_path)
                self._is_configured = False
                return False

        except Exception as err:
            logger.error("Failed to load hazard detection model at %s: %s", resolved_model_path, str(err))
            self._model = None
            self._model_type = None
            self._is_configured = False
            return False

    def set_test_model(
        self,
        inference_fn: Callable[[np.ndarray], List[Dict[str, Any]]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Injects a mock or test inference function for deterministic unit testing without external weights."""
        self._custom_inference_fn = inference_fn
        self._model = "test_custom_runner"
        self._model_type = "custom"
        self._metadata = metadata or {
            "model_name": "Test Synthetic Hazard Detector",
            "version": "0.1.0-test",
            "architecture": "Unit Test Mock Detector",
        }
        self._is_configured = True

    def reset(self) -> None:
        """Resets service back to unconfigured state."""
        self._model = None
        self._model_type = None
        self._metadata = {}
        self._is_configured = False
        self._custom_inference_fn = None

    def is_available(self) -> bool:
        """Returns True if a valid ML model is configured and ready for inference."""
        return self._is_configured and (self._model is not None or self._custom_inference_fn is not None)

    def get_metadata(self) -> Dict[str, Any]:
        """Returns metadata regarding active model, architecture, and validation limitations."""
        training_source = self._metadata.get("training_dataset")
        if not training_source and "dataset" in self._metadata:
            training_source = self._metadata["dataset"].get("source")

        return {
            "is_configured": self.is_available(),
            "model_type": self._model_type,
            "model_name": self._metadata.get("model_name", "Unconfigured Hazard Detector"),
            "version": self._metadata.get("version", "N/A"),
            "architecture": self._metadata.get("architecture", "Unknown"),
            "parameters": self._metadata.get("parameters", "3.0M"),
            "classes": self._metadata.get("classes", ["crater", "rock", "boulder", "escarpment"]),
            "training_dataset": training_source or "Not documented",
            "validation_domain": self._metadata.get("validation_domain", "Lunar South Pole Orbital Nadir Imagery (LROC NAC / OHRC)"),
            "evaluation_metrics": self._metadata.get("evaluation_metrics", {}),
            "performance_benchmarks": self._metadata.get("performance_benchmarks", {}),
            "operational_limitations": self._metadata.get("operational_limitations", {}),
            "apollo_domain_gap_warning": APOLLO_DOMAIN_LIMITATION,
        }

    # -----------------------------------------------------------------------
    # Input Validation & Decoding
    # -----------------------------------------------------------------------
    def validate_and_decode_image(
        self,
        image_input: Union[str, bytes],
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        """Validates input payload and decodes into a PIL Image.

        Raises ValueError with specific diagnostic messages on invalid, empty,
        or corrupted inputs.
        """
        raw_bytes: bytes

        if isinstance(image_input, bytes):
            raw_bytes = image_input
        elif isinstance(image_input, str):
            clean_str = image_input.strip()
            if not clean_str:
                raise ValueError("Image payload is empty (0 bytes).")

            # Check if input is a local file path
            if (len(clean_str) < 500) and (os.path.exists(clean_str) or Path(clean_str).is_file()):
                with open(clean_str, "rb") as f:
                    raw_bytes = f.read()
            else:
                # Base64 string: strip optional data URI scheme (e.g. data:image/png;base64,...)
                if "," in clean_str and clean_str.startswith("data:image/"):
                    clean_str = clean_str.split(",", 1)[1]

                try:
                    raw_bytes = base64.b64decode(clean_str, validate=True)
                except Exception as b64_err:
                    raise ValueError(f"Invalid base64 encoding: {str(b64_err)}") from b64_err
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input).__name__}")

        if len(raw_bytes) == 0:
            raise ValueError("Image payload is empty (0 bytes).")

        if len(raw_bytes) > hazard_settings.MAX_IMAGE_BYTES:
            raise ValueError(
                f"Image payload size ({len(raw_bytes) / 1024 / 1024:.1f} MB) exceeds maximum allowed "
                f"limit ({hazard_settings.MAX_IMAGE_BYTES / 1024 / 1024:.1f} MB)."
            )

        try:
            img = Image.open(io.BytesIO(raw_bytes))
            # Force verification of image header
            img.verify()
            # Reopen because verify() closes or invalidates image data
            img = Image.open(io.BytesIO(raw_bytes))
        except (UnidentifiedImageError, OSError, SyntaxError) as err:
            raise ValueError("Invalid image encoding or corrupted file header. Expected valid PNG, JPEG, or TIFF.") from err

        width, height = img.size
        if width <= 0 or height <= 0:
            raise ValueError("Image has invalid non-positive dimensions.")

        if width > hazard_settings.MAX_IMAGE_WIDTH or height > hazard_settings.MAX_IMAGE_HEIGHT:
            raise ValueError(
                f"Image dimensions ({width}x{height}) exceed maximum allowed size "
                f"({hazard_settings.MAX_IMAGE_WIDTH}x{hazard_settings.MAX_IMAGE_HEIGHT})."
            )

        meta = {
            "width": width,
            "height": height,
            "format": img.format or "UNKNOWN",
            "mode": img.mode,
            "byte_size": len(raw_bytes),
        }
        return img, meta

    # -----------------------------------------------------------------------
    # Image Preprocessing
    # -----------------------------------------------------------------------
    def preprocess_image(
        self,
        img: Image.Image,
        target_size: Optional[Tuple[int, int]] = None,
        channels: int = 1,
        normalize: bool = True,
    ) -> np.ndarray:
        """Preprocesses decoded image into normalized floating-point tensor array.

        Converts channels (Grayscale / RGB), resizes with bilinear interpolation,
        normalizes pixels to [0.0, 1.0], and formats to (1, C, H, W).
        """
        # Channel conversion
        if channels == 1:
            if img.mode != "L":
                img = img.convert("L")
        elif channels == 3:
            if img.mode != "RGB":
                img = img.convert("RGB")

        # Resizing
        if target_size:
            target_w, target_h = target_size
            if (img.width != target_w) or (img.height != target_h):
                img = img.resize((target_w, target_h), Image.Resampling.BILINEAR)

        arr = np.array(img, dtype=np.float32)

        # Normalization [0.0, 1.0]
        if normalize:
            max_val = 65535.0 if arr.max() > 255.0 else 255.0
            if max_val > 0:
                arr = arr / max_val

        # Add batch and channel dimensions (1, C, H, W)
        if channels == 1:
            arr = np.expand_dims(arr, axis=(0, 1))
        elif channels == 3:
            # (H, W, 3) -> (1, 3, H, W)
            arr = np.transpose(arr, (2, 0, 1))
            arr = np.expand_dims(arr, axis=0)

        return arr

    # -----------------------------------------------------------------------
    # Model Inference
    # -----------------------------------------------------------------------
    def infer(self, tensor: np.ndarray) -> Any:
        """Runs inference on preprocessed tensor.

        Raises RuntimeError on internal inference failures.
        """
        if not self.is_available():
            raise RuntimeError("Hazard detection model is not configured.")

        try:
            if self._custom_inference_fn is not None:
                return self._custom_inference_fn(tensor)

            if self._model_type == "yolo":
                results = self._model(tensor, verbose=False)[0]
                raw_boxes = []
                for b in results.boxes:
                    xmin, ymin, xmax, ymax = b.xyxy[0].tolist()
                    conf = float(b.conf[0])
                    cls_id = int(b.cls[0])
                    raw_boxes.append([ymin, xmin, ymax, xmax, conf, cls_id])
                return raw_boxes

            if self._model_type == "onnx":
                input_name = self._model.get_inputs()[0].name
                outputs = self._model.run(None, {input_name: tensor})
                return outputs

            if self._model_type == "torch":
                import torch

                device = next(self._model.parameters()).device if hasattr(self._model, "parameters") else "cpu"
                with torch.no_grad():
                    torch_tensor = torch.from_numpy(tensor).to(device)
                    raw_out = self._model(torch_tensor)
                    if isinstance(raw_out, torch.Tensor):
                        return raw_out.cpu().numpy()
                    elif isinstance(raw_out, (list, tuple)):
                        return [o.cpu().numpy() if isinstance(o, torch.Tensor) else o for o in raw_out]
                    elif isinstance(raw_out, dict):
                        return {k: v.cpu().numpy() if isinstance(v, torch.Tensor) else v for k, v in raw_out.items()}
                    return raw_out

            raise RuntimeError(f"Unknown model execution runtime: '{self._model_type}'")

        except Exception as e:
            logger.exception("Inference execution failure: %s", str(e))
            raise RuntimeError(f"Model inference execution failed: {str(e)}") from e

    # -----------------------------------------------------------------------
    # Output Postprocessing & Metric Calibration
    # -----------------------------------------------------------------------
    def postprocess(
        self,
        raw_output: Any,
        original_size: Tuple[int, int],
        confidence_threshold: float,
        spatial_resolution_mpp: Optional[float] = None,
    ) -> Tuple[List[DetectionItem], int, int, List[str]]:
        """Parses model outputs, filters by confidence threshold, applies metric spatial

        scaling where calibrated, and aggregates hazard counts.
        """
        detections: List[DetectionItem] = []
        warnings: List[str] = []
        orig_w, orig_h = original_size

        if spatial_resolution_mpp is None or spatial_resolution_mpp <= 0:
            warnings.append(
                "Optical image scale uncalibrated; real-world metric dimensions (meters) "
                "cannot be calculated without spatial resolution (meters per pixel)."
            )

        # Standard parsed detection items
        raw_items: List[Dict[str, Any]] = []
        class_map = {0: "crater", 1: "boulder", 2: "rock", 3: "escarpment"}
        if self._metadata.get("class_id_mapping"):
            for k, v in self._metadata["class_id_mapping"].items():
                try:
                    class_map[int(k)] = v
                except (ValueError, TypeError):
                    pass

        if isinstance(raw_output, list):
            # Format: list of detection dicts or numpy boxes
            for item in raw_output:
                if isinstance(item, dict):
                    raw_items.append(item)
                elif isinstance(item, (list, np.ndarray)) and len(item) >= 6:
                    # [ymin, xmin, ymax, xmax, score, class_id]
                    class_id = int(item[5])
                    raw_items.append({
                        "label": class_map.get(class_id, "crater"),
                        "confidence": float(item[4]),
                        "box": [float(item[0]), float(item[1]), float(item[2]), float(item[3])],
                    })
        elif isinstance(raw_output, np.ndarray):
            # Shape (N, 6): [ymin, xmin, ymax, xmax, score, class_id]
            if raw_output.ndim == 2 and raw_output.shape[1] >= 6:
                for row in raw_output:
                    class_id = int(row[5])
                    raw_items.append({
                        "label": class_map.get(class_id, "crater"),
                        "confidence": float(row[4]),
                        "box": [float(row[0]), float(row[1]), float(row[2]), float(row[3])],
                    })

        for item in raw_items:
            conf = float(item.get("confidence", item.get("score", 0.0)))
            if conf < confidence_threshold:
                continue

            label = str(item.get("label", "crater")).lower()
            if label not in ["crater", "rock", "boulder", "escarpment"]:
                label = "crater"

            # Parse bounding region
            raw_box = item.get("box") or item.get("bounding_box")
            bbox: Optional[BoundingBox] = None
            center_pix: Optional[List[int]] = None
            pixel_span: Optional[float] = None

            if raw_box is not None and len(raw_box) >= 4:
                ymin, xmin, ymax, xmax = [float(v) for v in raw_box[:4]]
                # Denormalize if box coordinates are in [0, 1]
                if ymax <= 1.0 and xmax <= 1.0:
                    ymin *= orig_h
                    ymax *= orig_h
                    xmin *= orig_w
                    xmax *= orig_w

                bbox = BoundingBox(
                    ymin=round(ymin, 1),
                    xmin=round(xmin, 1),
                    ymax=round(ymax, 1),
                    xmax=round(xmax, 1),
                )
                center_pix = [int(round((ymin + ymax) / 2.0)), int(round((xmin + xmax) / 2.0))]
                pixel_span = round(float(max(abs(ymax - ymin), abs(xmax - xmin))), 1)

            # Sizing calculation strictly respecting spatial calibration rule
            estimated_size_m: Optional[float] = None
            if spatial_resolution_mpp is not None and spatial_resolution_mpp > 0 and pixel_span is not None:
                estimated_size_m = round(pixel_span * spatial_resolution_mpp, 2)

            # Severity classification
            severity = "medium"
            if label == "crater":
                if estimated_size_m is not None:
                    severity = "critical" if estimated_size_m > 25.0 else ("high" if estimated_size_m > 10.0 else "medium")
                elif pixel_span is not None:
                    severity = "critical" if pixel_span > 100.0 else ("high" if pixel_span > 40.0 else "medium")
            elif label in ["rock", "boulder"]:
                if estimated_size_m is not None:
                    severity = "critical" if estimated_size_m > 2.0 else ("high" if estimated_size_m > 0.8 else "medium")
                elif pixel_span is not None:
                    severity = "high" if pixel_span > 20.0 else "medium"

            detections.append(
                DetectionItem(
                    label=label,
                    confidence=round(conf, 4),
                    bounding_box=bbox,
                    center_pixel=center_pix,
                    pixel_diameter=pixel_span,
                    estimated_size_m=estimated_size_m,
                    severity=severity,
                    mask_rle=item.get("mask_rle"),
                )
            )

        crater_count = sum(1 for d in detections if d.label == "crater")
        rock_count = sum(1 for d in detections if d.label in ["rock", "boulder"])

        return detections, crater_count, rock_count, warnings

    # -----------------------------------------------------------------------
    # Main Predict Entry Point
    # -----------------------------------------------------------------------
    def predict(self, req: HazardPredictRequest) -> HazardPredictResponse:
        """Executes full hazard prediction pipeline for an image payload.

        If no trained model is configured, returns Task 5 structured fallback
        without crashing the application.
        """
        # TASK 5: Graceful error handling when model is not available
        if not self.is_available():
            return HazardPredictResponse(
                status="not_available",
                detections=[],
                crater_count=None,
                rock_count=None,
                warnings=["Hazard detection model is not configured."],
                model_name=None,
                model_version=None,
                limitations=(
                    "No trained crater and rock detection model is currently loaded in Backend/data/models/. "
                    "Optical deep-learning hazard inference is offline."
                ),
            )

        # Validate image input existence
        if req.image_base64 is not None:
            img_source = req.image_base64
        elif req.image_path is not None:
            img_source = req.image_path
        else:
            raise ValueError("No image input provided. Expected 'image_base64' or 'image_path'.")

        # Decode and validate image
        pil_img, img_meta = self.validate_and_decode_image(img_source)

        conf_thresh = req.confidence_threshold or hazard_settings.DEFAULT_CONFIDENCE_THRESHOLD

        if self._model_type == "yolo" and self._custom_inference_fn is None:
            # High-performance native YOLO inference directly on PIL image
            results = self._model(pil_img, conf=conf_thresh, imgsz=640, verbose=False)[0]
            raw_outputs = []
            for b in results.boxes:
                xmin, ymin, xmax, ymax = b.xyxy[0].tolist()
                conf = float(b.conf[0])
                cls_id = int(b.cls[0])
                raw_outputs.append([ymin, xmin, ymax, xmax, conf, cls_id])
        else:
            # Determine target input size from metadata or default (512, 512)
            target_size = tuple(self._metadata.get("input_shape", [1, 1, 512, 512])[2:]) or (512, 512)
            channels = int(self._metadata.get("input_channels", 1))

            # Preprocessing
            tensor = self.preprocess_image(
                img=pil_img,
                target_size=target_size,
                channels=channels,
                normalize=True,
            )

            # Inference
            raw_outputs = self.infer(tensor)

        # Postprocessing
        detections, crater_count, rock_count, warnings = self.postprocess(
            raw_output=raw_outputs,
            original_size=(img_meta["width"], img_meta["height"]),
            confidence_threshold=conf_thresh,
            spatial_resolution_mpp=req.spatial_resolution_mpp,
        )

        model_name = self._metadata.get("model_name", "Lunar Hazard Detector")
        model_version = self._metadata.get("version", "1.0.0")

        # Generate visual detection overlay
        overlay_data_url = self.render_detection_overlay(pil_img, detections)

        return HazardPredictResponse(
            status="success",
            detections=detections,
            crater_count=crater_count,
            rock_count=rock_count,
            overlay_image=overlay_data_url,
            warnings=warnings,
            model_name=model_name,
            model_version=model_version,
            limitations=APOLLO_DOMAIN_LIMITATION,
        )

    @staticmethod
    def render_detection_overlay(
        img: Image.Image,
        detections: List[DetectionItem],
        max_dimension: int = 1024,
    ) -> str:
        """Draws bounding boxes and class labels onto lunar image and returns base64 PNG data URL."""
        from PIL import ImageDraw
        overlay_img = img.convert("RGB")
        orig_w, orig_h = overlay_img.size

        if max(orig_w, orig_h) > max_dimension:
            scale = max_dimension / max(orig_w, orig_h)
            new_w, new_h = int(orig_w * scale), int(orig_h * scale)
            overlay_img = overlay_img.resize((new_w, new_h), Image.Resampling.BILINEAR)
        else:
            scale = 1.0

        draw = ImageDraw.Draw(overlay_img)

        for det in detections:
            if not det.bounding_box:
                continue
            b = det.bounding_box
            ymin = b.ymin * scale
            xmin = b.xmin * scale
            ymax = b.ymax * scale
            xmax = b.xmax * scale

            label_lower = det.label.lower()
            if "crater" in label_lower:
                box_color = "#38BDF8"  # Cyan
                bg_color = "#38BDF8"
            else:
                box_color = "#F59E0B"  # Amber / Orange
                bg_color = "#F59E0B"

            draw.rectangle([xmin, ymin, xmax, ymax], outline=box_color, width=2)

            size_str = f" {det.estimated_size_m:.1f}m" if det.estimated_size_m is not None else ""
            tag = f"{det.label.upper()}{size_str} ({int(round(det.confidence * 100))}%)"
            tag_w = len(tag) * 6 + 6
            tag_top = max(0, ymin - 13)
            draw.rectangle([xmin, tag_top, xmin + tag_w, ymin], fill=bg_color)
            draw.text((xmin + 3, tag_top), tag, fill="#000000")

        buf = io.BytesIO()
        overlay_img.save(buf, format="PNG", optimize=True)
        b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64_data}"


hazard_detection_service = HazardDetectionService()
