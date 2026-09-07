import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(ROOT_DIR))

print("=== STEP 1: PYTHON ENVIRONMENT & IMPORTS ===")
print(f"Python: {sys.executable}")
print(f"Working directory: {os.getcwd()}")

has_yolo = False
try:
    from ultralytics import YOLO
    has_yolo = True
    print("[OK] ultralytics is INSTALLED")
except ImportError as e:
    print(f"[NO] ultralytics is NOT installed: {e}")

has_ort = False
try:
    import onnxruntime as ort
    has_ort = True
    print(f"[OK] onnxruntime is INSTALLED (version {ort.__version__})")
except ImportError as e:
    print(f"[NO] onnxruntime is NOT installed: {e}")

has_cv2 = False
try:
    import cv2
    has_cv2 = True
    print(f"[OK] cv2 is INSTALLED (version {cv2.__version__})")
except ImportError as e:
    print(f"[NO] cv2 is NOT installed: {e}")

print("\n=== STEP 2: SEARCHING FOR MODEL FILES (.pt, .onnx) ===")
search_dirs = [
    ROOT_DIR,
    BACKEND_DIR,
    BACKEND_DIR / "models",
    ROOT_DIR / "models",
    Path.home() / ".cache",
]

found_models = []
for d in search_dirs:
    if d.exists():
        for ext in ["*.pt", "*.onnx", "*.engine"]:
            for f in d.rglob(ext):
                # Skip venv files to avoid noise
                if ".venv" in str(f) or "site-packages" in str(f) or "node_modules" in str(f):
                    continue
                found_models.append(f)

print(f"Found {len(found_models)} model file(s):")
for m in found_models:
    print(f"  - {m} ({m.stat().st_size / 1e6:.2f} MB)")

print("\n=== STEP 3: CHECKING FASTALPR / OPEN_IMAGE_MODELS ===")
try:
    from open_image_models.detection.core.hub import MODEL_CACHE_DIR, DETECTION_MODELS
    print(f"open_image_models cache dir: {MODEL_CACHE_DIR}")
    if MODEL_CACHE_DIR.exists():
        for f in MODEL_CACHE_DIR.glob("*"):
            print(f"  Cached: {f.name} ({f.stat().st_size / 1e6:.2f} MB)")
except Exception as e:
    print(f"Error checking open_image_models: {e}")

print("\n=== STEP 4: INSPECTING TEST FRAME (EVT-4E2FA0.jpg) ===")
test_frame_path = BACKEND_DIR / "data" / "evidence" / "EVT-4E2FA0.jpg"
if test_frame_path.exists():
    img = cv2.imread(str(test_frame_path))
    if img is not None:
        print(f"Loaded test frame: {img.shape} (WxH={img.shape[1]}x{img.shape[0]})")
    else:
        print("Failed to read image")
else:
    print(f"File not found: {test_frame_path}")
