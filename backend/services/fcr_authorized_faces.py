"""Authorized Personnel Face Store for IBVAP.
Independent face embedding registry for authorized/registered personnel.
Separate from the Persons of Interest (Watchlist) registry.

Stores face embeddings in fcr_authorized_faces.json so that the detection
pipeline can independently compare a detected face against:
  1. Watchlist (Persons of Interest) → "Watchlist Match"
  2. Authorized Personnel faces     → "Authorized Person"
  3. Neither                        → "Unknown Person"
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
AUTH_FACES_FILE = DATA_DIR / "fcr_authorized_faces.json"


def _ensure_storage():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not AUTH_FACES_FILE.exists():
        with open(AUTH_FACES_FILE, "w") as f:
            json.dump([], f)


_ensure_storage()


def get_authorized_faces():
    """Returns all enrolled authorized personnel face entries."""
    _ensure_storage()
    try:
        with open(AUTH_FACES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save_faces(faces_list):
    _ensure_storage()
    with open(AUTH_FACES_FILE, "w") as f:
        json.dump(faces_list, f, indent=2)


def enroll_authorized_face(name: str, image_bytes: bytes,
                           left_image_bytes: bytes = None,
                           right_image_bytes: bytes = None,
                           face_id: str = None):
    """Enrolls a face for an authorized person.
    Requires exactly 1 clear face in the primary (front) image.
    Optionally accepts left and right profile images for multi-angle matching.
    If an existing face entry matches face_id or name, it is updated in-place.
    """
    _ensure_storage()

    if not _has_cv2:
        raise ValueError("OpenCV is not available to decode the image.")

    # Decode and detect front face
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Could not decode image file. Please upload a valid JPG/PNG image.")

    faces = face_engine.detect_faces(frame)
    if len(faces) == 0:
        raise ValueError("No face found in uploaded image. Please ensure good lighting and front-facing angle.")
    if len(faces) > 1:
        raise ValueError(f"Upload one clear face only. Found {len(faces)} faces in the image.")

    target_face = faces[0]
    front_embedding = target_face["embedding"]
    bbox = target_face["bbox"]

    # Build embeddings list (front is always first)
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

    # Generate thumbnail from front face
    x1, y1, x2, y2 = bbox
    crop = frame[max(0, y1):min(frame.shape[0], y2), max(0, x1):min(frame.shape[1], x2)]
    thumb_b64 = ""
    if crop.size > 0:
        _, thumb_jpg = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 80])
        thumb_b64 = base64.b64encode(thumb_jpg).decode("utf-8")

    faces_list = get_authorized_faces()
    now = datetime.utcnow().isoformat() + "Z"

    # Check if updating an existing record by face_id or exact name
    existing_idx = -1
    target_id = face_id
    if target_id:
        for idx, item in enumerate(faces_list):
            if item.get("id") == target_id:
                existing_idx = idx
                break

    if existing_idx == -1:
        query = name.strip().lower()
        for idx, item in enumerate(faces_list):
            if item.get("name", "").strip().lower() == query:
                existing_idx = idx
                target_id = item.get("id")
                break

    if existing_idx != -1:
        entry_id = target_id or faces_list[existing_idx].get("id") or f"auth-{uuid.uuid4().hex[:8]}"
        created_at = faces_list[existing_idx].get("created_at", now)
        entry = {
            "id": entry_id,
            "name": name.strip(),
            "embedding": front_embedding,       # backward compat: single front embedding
            "embeddings": embeddings,            # multi-angle embeddings
            "embedding_labels": embedding_labels,
            "confidence": target_face["confidence"],
            "bbox": bbox,
            "thumbnail": thumb_b64,
            "created_at": created_at,
            "updated_at": now,
        }
        faces_list[existing_idx] = entry
    else:
        entry_id = target_id or f"auth-{uuid.uuid4().hex[:8]}"
        entry = {
            "id": entry_id,
            "name": name.strip(),
            "embedding": front_embedding,       # backward compat: single front embedding
            "embeddings": embeddings,            # multi-angle embeddings
            "embedding_labels": embedding_labels,
            "confidence": target_face["confidence"],
            "bbox": bbox,
            "thumbnail": thumb_b64,
            "created_at": now,
        }
        faces_list.append(entry)

    _save_faces(faces_list)

    return {
        "id": entry_id,
        "name": name.strip(),
        "confidence": target_face["confidence"],
        "embedding_count": len(embeddings),
        "created_at": now,
        "status": "Enrolled successfully as authorized personnel",
    }


def delete_authorized_face(face_id: str):
    """Removes an authorized face entry by face_id."""
    faces_list = get_authorized_faces()
    updated = [item for item in faces_list if item["id"] != face_id]
    _save_faces(updated)
    return len(updated) < len(faces_list)


def get_face_by_name(name: str):
    """Finds an authorized face entry by name (case-insensitive partial match)."""
    if not name:
        return None
    query = name.strip().lower()
    for entry in get_authorized_faces():
        if entry.get("name", "").strip().lower() == query:
            return entry
    return None
