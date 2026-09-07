"""FCR Watchlist Service for IBVAP:
Handles image upload, face validation, embedding extraction, and persistent watchlist storage.
"""

import os, json, uuid, base64
from pathlib import Path
from datetime import datetime
from services import face_engine

try:
    import cv2
    import numpy as np
    _has_cv2 = True
except Exception:
    _has_cv2 = False

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
WATCHLIST_FILE = DATA_DIR / "fcr_watchlist.json"
MATCHES_FILE = DATA_DIR / "fcr_matches.json"

_recent_matches = []


def _ensure_storage():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not WATCHLIST_FILE.exists():
        with open(WATCHLIST_FILE, "w") as f:
            json.dump([], f)
    if not MATCHES_FILE.exists():
        with open(MATCHES_FILE, "w") as f:
            json.dump([], f)


_ensure_storage()


def get_watchlist():
    _ensure_storage()
    try:
        with open(WATCHLIST_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def enroll_target_image(name: str, image_bytes: bytes,
                        left_image_bytes: bytes = None,
                        right_image_bytes: bytes = None):
    """Enrolls a target person from an uploaded image file.
    Rules:
    1. Must contain exactly 1 clear face in the front (primary) image.
    2. Rejects if 0 faces or >1 faces found in primary image.
    3. Extracts embedding and saves to watchlist.
    4. Optionally accepts left/right profile images for multi-angle matching.
    """
    _ensure_storage()

    if not _has_cv2:
        raise ValueError("OpenCV is not available to decode the image.")

    # Decode primary (front) image from bytes
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Could not decode image file. Please upload a valid JPG/PNG image.")

    # Detect faces in front image
    faces = face_engine.detect_faces(frame)

    if len(faces) == 0:
        raise ValueError("No face found in uploaded image. Please ensure good lighting and front-facing angle.")
    if len(faces) > 1:
        raise ValueError(f"Upload one clear face only. Found {len(faces)} faces in the image.")

    target_face = faces[0]
    bbox = target_face["bbox"]
    front_embedding = target_face["embedding"]

    # Build multi-angle embeddings list
    embeddings = [front_embedding]
    embedding_labels = ["front"]

    # Optional left profile
    if left_image_bytes:
        try:
            left_arr = np.frombuffer(left_image_bytes, np.uint8)
            left_frame = cv2.imdecode(left_arr, cv2.IMREAD_COLOR)
            if left_frame is not None:
                left_faces = face_engine.detect_faces(left_frame)
                if len(left_faces) >= 1:
                    embeddings.append(left_faces[0]["embedding"])
                    embedding_labels.append("left")
        except Exception:
            pass

    # Optional right profile
    if right_image_bytes:
        try:
            right_arr = np.frombuffer(right_image_bytes, np.uint8)
            right_frame = cv2.imdecode(right_arr, cv2.IMREAD_COLOR)
            if right_frame is not None:
                right_faces = face_engine.detect_faces(right_frame)
                if len(right_faces) >= 1:
                    embeddings.append(right_faces[0]["embedding"])
                    embedding_labels.append("right")
        except Exception:
            pass

    # Generate small thumbnail from front face
    x1, y1, x2, y2 = bbox
    crop = frame[max(0, y1):min(frame.shape[0], y2), max(0, x1):min(frame.shape[1], x2)]
    thumb_b64 = ""
    if crop.size > 0:
        _, thumb_jpg = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 80])
        thumb_b64 = base64.b64encode(thumb_jpg).decode("utf-8")

    face_id = f"fcr-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat() + "Z"

    entry = {
        "id": face_id,
        "name": name.strip(),
        "embedding": front_embedding,       # backward compat: single front embedding
        "embeddings": embeddings,            # multi-angle embeddings array
        "embedding_labels": embedding_labels,
        "confidence": target_face["confidence"],
        "bbox": bbox,
        "thumbnail": thumb_b64,
        "created_at": now
    }

    watchlist = get_watchlist()
    watchlist.append(entry)

    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlist, f, indent=2)

    return {
        "id": face_id,
        "name": name.strip(),
        "confidence": target_face["confidence"],
        "embedding_count": len(embeddings),
        "created_at": now,
        "status": "Enrolled successfully"
    }


def delete_from_watchlist(face_id: str):
    _ensure_storage()
    watchlist = get_watchlist()
    updated = [item for item in watchlist if item["id"] != face_id]
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(updated, f, indent=2)
    return len(updated) < len(watchlist)


def log_match(match_record: dict):
    global _recent_matches
    _recent_matches.insert(0, match_record)
    if len(_recent_matches) > 50:
        _recent_matches = _recent_matches[:50]


def get_recent_matches():
    return list(_recent_matches)
