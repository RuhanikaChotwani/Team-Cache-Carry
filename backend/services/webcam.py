"""Webcam and Video Capture Service for IBVAP.
High-Performance Decoupled AI Pipeline:
- Native capture thread with double-buffered ring queue for smooth 20-30 FPS MJPEG streaming.
- Asynchronous AI inference worker (YuNet face recognition, FastALPR, animal detection).
- DeepSORT / IoU persistent tracking with First-Entry Evidence preservation.
- Anomaly Rule Engine integration (Authorized vs Unknown Person, Registered vs Unregistered Vehicle, Animal Threat).
- Tamper-proof blockchain evidence anchoring and append-only frame hashing.
"""

import os
import time
import threading
import uuid
import logging
import queue
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, List, Dict, Any

from services import (
    face_engine,
    fcr_watchlist,
    fcr_authorized_faces,
    anpr_engine,
    alert_store,
    ledger,
    video_manager,
    storage,
    blockchain,
    anomaly_engine,
    model_loader,
)

logger = logging.getLogger("ibvap.webcam")

_has_cv2 = False
_has_np = False

try:
    import cv2
    import numpy as np
    _has_cv2 = True
    _has_np = True
except Exception:
    pass

# --- Global Atomic Lifecycle State ---
_lifecycle_lock = threading.Lock()
_stream_session_id = 0
_frame_session_id = 0

_cap = None
_running = False
_camera_error: Optional[str] = None
_last_frame_error: Optional[str] = None
_stop_event = threading.Event()
_capture_thread: Optional[threading.Thread] = None
_ai_thread: Optional[threading.Thread] = None

_frames_published = 0
_last_valid_frame_at = 0.0

# Source metadata
_source_type = "webcam"
_source_name = "Laptop Webcam 0"
_source_path: Union[int, str] = 0
_loop_enabled = True
_source_finished = False
_current_frame_number = 0
_total_frames = 0
_video_fps = 30.0

# FPS telemetry
_displayed_fps = 0.0
_inference_fps = 0.0

# Frame and detection cache
_latest_raw_frame: Optional[bytes] = None
_latest_annotated_frame: Optional[bytes] = None
_latest_debug_frame: Optional[bytes] = None

_latest_faces: List[dict] = []
_latest_confirmed_plates: List[dict] = []
_latest_entities: List[dict] = []

_frame_width = 640
_frame_height = 480
_frame_lock = threading.Lock()
_detection_lock = threading.Lock()

# Thread-safe single-slot inference handoff
_inference_slot_lock = threading.Lock()
_inference_frame_packet: Optional[dict] = None  # {frame, infer_scale, w, h, frame_counter, raw_hash_bytes}

# First-Entry Evidence and Track Registry
# track_id -> {
#   "track_id": str,
#   "class": str,
#   "classification": str,
#   "bbox": [x1, y1, x2, y2],
#   "first_entry_bytes": bytes,
#   "first_entry_time": str,
#   "first_frame_num": int,
#   "last_seen": float,
#   "hits": int,
#   "identity": str,
#   "plate_text": str,
#   "is_authorized": bool,
#   "alert_fired": bool
# }
_tracked_entities: Dict[str, dict] = {}
_entity_counter = 0

_hog_detector = None
if _has_cv2:
    try:
        _hog = cv2.HOGDescriptor()
        _hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        _hog_detector = _hog
    except Exception:
        _hog_detector = None

_last_alert_time: Dict[str, float] = {}


def get_status() -> dict:
    global _running, _cap, _has_cv2, _camera_error, _last_frame_error
    global _frames_published, _last_valid_frame_at, _stream_session_id
    global _source_name, _source_type, _source_finished, _loop_enabled
    global _current_frame_number, _total_frames, _displayed_fps, _inference_fps
    global _frame_width, _frame_height

    is_open = False
    if _cap is not None and _has_cv2:
        try:
            is_open = bool(_cap.isOpened())
        except Exception:
            pass

    now = time.time()
    is_feed_active = (
        _running
        and is_open
        and _frames_published > 0
        and _last_valid_frame_at > 0
        and (now - _last_valid_frame_at < 2.5)
    )

    f_status = face_engine.get_face_engine_status() or {}
    a_status = anpr_engine.get_status() or {}

    yunet_loaded = bool(f_status.get("yunet_loaded", False))
    sface_loaded = bool(f_status.get("sface_loaded", False))
    alpr_loaded = bool(a_status.get("alpr_loaded", False))

    with _detection_lock:
        faces_count = len(_latest_faces) if is_feed_active else 0
        plates_count = len(_latest_confirmed_plates) if is_feed_active else 0
        entities_count = len(_latest_entities) if is_feed_active else 0

    return {
        "running": is_feed_active,
        "feed_active": is_feed_active,
        "is_camera_open": is_open,
        "session_id": _stream_session_id,
        "camera_error": _camera_error or _last_frame_error,
        "last_frame_error": _last_frame_error,
        "frames_published": _frames_published,
        "last_valid_frame_at": _last_valid_frame_at if _last_valid_frame_at > 0 else None,
        "source": _source_name if is_feed_active else (_camera_error or f"Connecting to {_source_name}..."),
        "source_type": _source_type,
        "source_name": _source_name,
        "source_finished": _source_finished,
        "loop_enabled": _loop_enabled,
        "frame_number": _current_frame_number,
        "total_frames": _total_frames if _total_frames > 0 else None,
        "displayed_fps": round(_displayed_fps, 1) if is_feed_active else 0.0,
        "inference_fps": round(_inference_fps, 1) if is_feed_active else 0.0,
        "face_count": faces_count,
        "plate_count": plates_count,
        "entity_count": entities_count,
        "current_frame_width": _frame_width,
        "current_frame_height": _frame_height,
        "face_detector_name": "YuNet Face Detector (2023mar)",
        "watchlist_count": len(fcr_watchlist.get_watchlist()),
        "model_loading_state": {
            "yunet": yunet_loaded,
            "sface": sface_loaded,
            "fast_alpr": alpr_loaded,
        },
        "models": {
            "yunet": {"loaded": yunet_loaded, "error": f_status.get("yunet_error")},
            "sface": {"loaded": sface_loaded, "error": f_status.get("sface_error")},
            "fast_alpr": {"loaded": alpr_loaded, "error": a_status.get("alpr_error")},
        },
    }


def start(
    source: Union[int, str] = 0,
    source_type: str = "webcam",
    source_id: Optional[str] = None,
    source_name: Optional[str] = None,
    loop: bool = True,
) -> dict:
    """Atomic start of a video capture session with decoupled workers."""
    global _cap, _running, _camera_error, _last_frame_error, _stop_event
    global _capture_thread, _ai_thread
    global _source_type, _source_name, _source_path, _loop_enabled, _source_finished
    global _current_frame_number, _total_frames, _video_fps, _stream_session_id, _frame_session_id
    global _frame_width, _frame_height, _displayed_fps, _inference_fps
    global _frames_published, _last_valid_frame_at
    global _latest_raw_frame, _latest_annotated_frame, _latest_debug_frame
    global _latest_faces, _latest_confirmed_plates, _latest_entities
    global _tracked_entities, _inference_frame_packet

    with _lifecycle_lock:
        _stop_event.set()
        _running = False

        if _capture_thread is not None and _capture_thread.is_alive():
            if _capture_thread != threading.current_thread():
                _capture_thread.join(timeout=1.5)
            _capture_thread = None

        if _ai_thread is not None and _ai_thread.is_alive():
            if _ai_thread != threading.current_thread():
                _ai_thread.join(timeout=1.5)
            _ai_thread = None

        if _cap is not None:
            try:
                _cap.release()
            except Exception:
                pass
            _cap = None

        ledger.stop_frame_chain()

        _stream_session_id += 1
        current_session = _stream_session_id
        _frame_session_id = 0
        _stop_event.clear()
        _camera_error = None
        _last_frame_error = None
        _source_finished = False
        _current_frame_number = 0
        _total_frames = 0
        _video_fps = 30.0
        _displayed_fps = 0.0
        _inference_fps = 0.0
        _frames_published = 0
        _last_valid_frame_at = 0.0

        with _frame_lock:
            _latest_raw_frame = None
            _latest_annotated_frame = None
            _latest_debug_frame = None

        with _detection_lock:
            _latest_faces = []
            _latest_confirmed_plates = []
            _latest_entities = []
            _tracked_entities = {}

        with _inference_slot_lock:
            _inference_frame_packet = None

        # Resolve Source
        _source_type = source_type
        _loop_enabled = loop

        if source_type == "webcam":
            _source_name = "Laptop Optical Sensor (Webcam 0)"
            _source_path = int(source) if str(source).isdigit() else 0
        elif source_type == "demo_video":
            meta = video_manager.get_video_by_id(str(source_id or source))
            if meta and meta.get("path") and os.path.exists(meta["path"]):
                _source_name = meta["name"]
                _source_path = meta["path"]
            else:
                resolved_path, resolved_name = video_manager.resolve_video_path("demo_video", source_id or source)
                if resolved_path and os.path.exists(resolved_path):
                    _source_name = resolved_name
                    _source_path = resolved_path
                else:
                    _camera_error = f"Demo video '{source_id or source}' not found on server."
                    return get_status()
        elif source_type == "uploaded_video":
            meta = video_manager.get_uploaded_video_by_id(str(source_id or source))
            if meta and meta.get("path") and os.path.exists(meta["path"]):
                _source_name = source_name or meta["name"]
                _source_path = meta["path"]
            else:
                resolved_path, resolved_name = video_manager.resolve_video_path("uploaded_video", source_id or source)
                if resolved_path and os.path.exists(resolved_path):
                    _source_name = source_name or resolved_name
                    _source_path = resolved_path
                else:
                    _camera_error = f"Uploaded video '{source_id or source}' not found."
                    return get_status()
        else:
            resolved_path, resolved_name = video_manager.resolve_video_path(source_type, source)
            if resolved_path and os.path.exists(resolved_path):
                _source_name = resolved_name
                _source_path = resolved_path
            else:
                _source_name = f"Source: {source}"
                _source_path = source

        if not _has_cv2:
            _camera_error = "OpenCV (cv2) is not installed."
            return get_status()

        # Open capture device
        try:
            if _source_type == "webcam":
                _cap = cv2.VideoCapture(_source_path, cv2.CAP_DSHOW)
                if not _cap.isOpened():
                    _cap = cv2.VideoCapture(_source_path)
            else:
                _cap = cv2.VideoCapture(str(_source_path))

            if not _cap.isOpened():
                _camera_error = f"Could not open source: {_source_name}"
                return get_status()

            if _source_type == "webcam":
                _cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                _cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            _frame_width = int(_cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
            _frame_height = int(_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
            _total_frames = int(_cap.get(cv2.CAP_PROP_FRAME_COUNT)) if _source_type != "webcam" else 0
            _video_fps = float(_cap.get(cv2.CAP_PROP_FPS)) or 30.0
            if _video_fps <= 0 or _video_fps > 60:
                _video_fps = 30.0

        except Exception as e:
            _camera_error = f"Error opening capture: {e}"
            return get_status()

        _running = True

        # Start frame chain session
        session_tag = f"{_source_type}_{current_session}_{int(time.time())}"
        ledger.start_frame_chain(session_tag)

        # Launch decoupled capture and AI threads
        _capture_thread = threading.Thread(
            target=_capture_loop,
            args=(current_session,),
            name=f"CaptureWorker-{current_session}",
            daemon=True,
        )
        _capture_thread.start()

        _ai_thread = threading.Thread(
            target=_ai_worker_loop,
            args=(current_session,),
            name=f"AIWorker-{current_session}",
            daemon=True,
        )
        _ai_thread.start()

        logger.info(f"Started streaming session {current_session} for '{_source_name}' at {_video_fps:.1f} FPS")
        return get_status()


def stop() -> dict:
    """Stops the active capture session atomically."""
    global _cap, _running, _latest_faces, _latest_confirmed_plates, _latest_entities
    global _latest_raw_frame, _latest_annotated_frame, _latest_debug_frame
    global _stop_event, _capture_thread, _ai_thread, _stream_session_id, _frame_session_id
    global _frames_published, _last_valid_frame_at

    with _lifecycle_lock:
        _stop_event.set()
        _running = False

        if _capture_thread is not None and _capture_thread.is_alive():
            if _capture_thread != threading.current_thread():
                _capture_thread.join(timeout=1.5)
            _capture_thread = None

        if _ai_thread is not None and _ai_thread.is_alive():
            if _ai_thread != threading.current_thread():
                _ai_thread.join(timeout=1.5)
            _ai_thread = None

        if _cap is not None:
            try:
                _cap.release()
            except Exception:
                pass
            _cap = None

        ledger.stop_frame_chain()
        _frames_published = 0
        _last_valid_frame_at = 0.0

        with _detection_lock:
            _latest_faces = []
            _latest_confirmed_plates = []
            _latest_entities = []

        with _frame_lock:
            _latest_raw_frame = None
            _latest_annotated_frame = None
            _latest_debug_frame = None
            _frame_session_id = 0

        logger.info("Stopped active capture stream.")
        return get_status()


def raw_mjpeg_generator(session_id: Optional[int] = None):
    """Streams unannotated JPEG frames at high framerate."""
    while True:
        if session_id is not None and session_id != _stream_session_id:
            break

        frame_bytes = None
        current_sess = _stream_session_id
        with _frame_lock:
            if _frame_session_id == current_sess and _latest_raw_frame is not None:
                frame_bytes = _latest_raw_frame

        if frame_bytes is None or len(frame_bytes) < 4000:
            if _camera_error:
                frame_bytes = _draw_status_card("SOURCE ERROR", _camera_error, (239, 75, 95))
            elif _source_finished:
                frame_bytes = _draw_status_card("PLAYBACK COMPLETED", f"Source: {_source_name}", (22, 185, 201))
            elif not _running:
                frame_bytes = _draw_status_card("SENSOR STANDBY", "Select video source or start webcam", (22, 185, 201))
            else:
                frame_bytes = _draw_status_card("CONNECTING...", f"Connecting to {_source_name}...", (255, 159, 67))

        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        time.sleep(0.033)


def ai_mjpeg_generator(session_id: Optional[int] = None):
    """Streams annotated HUD JPEG frames with zero lag at 20-30 FPS."""
    while True:
        if session_id is not None and session_id != _stream_session_id:
            break

        frame_bytes = None
        current_sess = _stream_session_id
        with _frame_lock:
            if _frame_session_id == current_sess and _latest_annotated_frame is not None:
                frame_bytes = _latest_annotated_frame

        if frame_bytes is None or len(frame_bytes) < 4000:
            if _camera_error:
                frame_bytes = _draw_status_card("SOURCE ERROR", _camera_error, (239, 75, 95))
            elif _source_finished:
                frame_bytes = _draw_status_card("PLAYBACK COMPLETED", f"Source: {_source_name}", (22, 185, 201))
            elif not _running:
                frame_bytes = _draw_status_card("SENSOR STANDBY", "Select video source or start webcam", (22, 185, 201))
            else:
                frame_bytes = _draw_status_card("CONNECTING...", f"Connecting to {_source_name}...", (255, 159, 67))

        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        time.sleep(0.033)


def get_debug_face_frame() -> bytes:
    with _frame_lock:
        if _latest_debug_frame is not None:
            return _latest_debug_frame
    return _draw_status_card("DIAGNOSTIC FEED", "Start a source to generate diagnostic frames")


def get_detections_payload() -> dict:
    """Returns JSON detection payload including faces, plates, and classified entities."""
    with _detection_lock:
        faces_list = list(_latest_faces)
        confirmed_list = list(_latest_confirmed_plates)
        raw_entities = list(_latest_entities)

    clean_entities = []
    for e in raw_entities:
        clean_e = {k: v for k, v in e.items() if k != "first_entry_bytes"}
        clean_entities.append(clean_e)

    f_status = face_engine.get_face_engine_status() or {}

    return {
        "faces": faces_list,
        "plates": confirmed_list,
        "entities": clean_entities,
        "counts": {
            "faces": len(faces_list),
            "plates": len(confirmed_list),
            "entities": len(clean_entities),
        },
        "debug": {
            "face_detector_loaded": bool(f_status.get("yunet_loaded", False)),
            "face_detector_name": "YuNet Face Detector (2023mar)",
            "displayed_fps": round(_displayed_fps, 1),
            "inference_fps": round(_inference_fps, 1),
        },
    }


# --- Decoupled Capture Loop (Display Thread: Fast 25-30 FPS) ---

def _capture_loop(session_id: int):
    global _latest_raw_frame, _latest_annotated_frame, _latest_debug_frame
    global _frame_width, _frame_height, _camera_error, _last_frame_error, _current_frame_number
    global _source_finished, _running, _cap, _stream_session_id, _frame_session_id
    global _displayed_fps, _frames_published, _last_valid_frame_at
    global _inference_frame_packet

    target_interval = 1.0 / max(15.0, min(_video_fps, 30.0))
    frame_counter = 0
    fps_t0 = time.time()
    disp_count = 0

    while not _stop_event.is_set():
        if session_id != _stream_session_id:
            break

        loop_start = time.time()
        try:
            if _cap is None or not _has_cv2 or not _cap.isOpened():
                _stop_event.wait(0.05)
                continue

            ret, frame = _cap.read()

            if not ret or frame is None:
                if _source_type != "webcam":
                    if _loop_enabled:
                        _cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = _cap.read()
                        if not ret or frame is None:
                            if session_id == _stream_session_id:
                                _source_finished = True
                                _running = False
                            break
                    else:
                        if session_id == _stream_session_id:
                            _source_finished = True
                            _running = False
                        break
                else:
                    _last_frame_error = "Webcam read returned empty frame"
                    _stop_event.wait(0.05)
                    continue

            frame_counter += 1
            disp_count += 1

            if _source_type != "webcam":
                try:
                    _current_frame_number = int(_cap.get(cv2.CAP_PROP_POS_FRAMES))
                except Exception:
                    _current_frame_number = frame_counter
            else:
                _current_frame_number = frame_counter

            h, w = frame.shape[:2]
            _frame_width = w
            _frame_height = h

            # Scales
            infer_scale = 960.0 / w if w > 960 else 1.0
            disp_scale = 1280.0 / w if w > 1280 else 1.0

            if disp_scale < 1.0:
                disp_w = 1280
                disp_h = int(h * disp_scale)
                disp_frame = cv2.resize(frame, (disp_w, disp_h))
            else:
                disp_frame = frame

            # Encode raw JPEG bytes for display and hashing
            _, r_jpg = cv2.imencode(".jpg", disp_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            raw_bytes = r_jpg.tobytes()

            # Append-only frame hashing for audit trail
            ledger.enqueue_frame_hash(raw_bytes, frame_counter, _source_name)

            # Pass latest frame to AI Worker via single-slot packet (non-blocking)
            with _inference_slot_lock:
                _inference_frame_packet = {
                    "frame": frame,
                    "infer_scale": infer_scale,
                    "w": w,
                    "h": h,
                    "frame_counter": frame_counter,
                    "raw_bytes": raw_bytes,
                    "disp_scale": disp_scale,
                }

            # Render overlay with latest tracked detections
            with _detection_lock:
                current_faces = list(_latest_faces)
                current_plates = list(_latest_confirmed_plates)
                current_entities = list(_latest_entities)

            annotated_frame = disp_frame.copy()
            _draw_surveillance_overlay(
                annotated_frame, current_faces, current_plates, current_entities,
                _source_name, disp_scale
            )
            _, a_jpg = cv2.imencode(".jpg", annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            annotated_bytes = a_jpg.tobytes()

            # Publish frames to streams
            if session_id == _stream_session_id and len(annotated_bytes) >= 4000:
                with _frame_lock:
                    _latest_raw_frame = raw_bytes
                    _latest_annotated_frame = annotated_bytes
                    _frame_session_id = session_id
                    _frames_published += 1
                    _last_valid_frame_at = time.time()
                    _last_frame_error = None

            # Calculate Display FPS
            now = time.time()
            if now - fps_t0 >= 1.0:
                _displayed_fps = disp_count / (now - fps_t0)
                disp_count = 0
                fps_t0 = now

        except Exception as e:
            logger.warning(f"Capture loop error: {e}")
            _last_frame_error = str(e)

        elapsed = time.time() - loop_start
        sleep_dur = max(0.001, target_interval - elapsed)
        time.sleep(sleep_dur)

    if session_id == _stream_session_id:
        ledger.stop_frame_chain()


# --- Asynchronous AI Worker Loop (DeepSORT tracking + FCR + ANPR + Anomaly Engine) ---

def _ai_worker_loop(session_id: int):
    global _latest_faces, _latest_confirmed_plates, _latest_entities
    global _tracked_entities, _entity_counter, _inference_fps

    infer_count = 0
    infer_t0 = time.time()
    zones = storage.get_zones()

    while not _stop_event.is_set():
        if session_id != _stream_session_id:
            break

        packet = None
        with _inference_slot_lock:
            if _inference_frame_packet is not None:
                packet = _inference_frame_packet
                # Clear slot so worker waits for fresh frame

        if packet is None:
            time.sleep(0.02)
            continue

        try:
            infer_count += 1
            frame = packet["frame"]
            infer_scale = packet["infer_scale"]
            w, h = packet["w"], packet["h"]
            frame_counter = packet["frame_counter"]
            raw_bytes = packet["raw_bytes"]

            if infer_scale < 1.0:
                infer_w = int(w * infer_scale)
                infer_h = int(h * infer_scale)
                infer_frame = cv2.resize(frame, (infer_w, infer_h))
            else:
                infer_frame = frame

            now_time = time.time()
            now_iso = datetime.utcnow().isoformat() + "Z"

            detected_entities_this_frame = []
            faces_payload = []
            confirmed_plates = []

            # -------------------------------------------------------------
            # 1. Face Detection (YuNet) & Dual-Registry Recognition (SFace)
            #    Compare against BOTH registries independently:
            #      - Watchlist (Persons of Interest) → "Watchlist Match"
            #      - Authorized Personnel faces     → "Authorized Person"
            #      - Neither                        → "Unknown Person"
            #    Priority: Watchlist Match > Authorized Person > Unknown
            # -------------------------------------------------------------
            accepted_faces, _, _, _ = face_engine.detect_faces_debug(infer_frame)
            watchlist = fcr_watchlist.get_watchlist()
            auth_faces = fcr_authorized_faces.get_authorized_faces()

            for idx, f in enumerate(accepted_faces):
                bx1, by1, bx2, by2 = f["bbox"]
                orig_bbox = [
                    max(0, int(bx1 / infer_scale)),
                    max(0, int(by1 / infer_scale)),
                    min(w, int(bx2 / infer_scale)),
                    min(h, int(by2 / infer_scale)),
                ]
                conf = f["confidence"]
                emb = f["embedding"]

                # Compare against Watchlist (Persons of Interest)
                wl_target, wl_score, wl_match = face_engine.compare_embedding(
                    emb, watchlist, threshold=0.55
                )

                # Compare against Authorized Personnel faces
                auth_target, auth_score, auth_match = face_engine.compare_embedding(
                    emb, auth_faces, threshold=0.55
                )

                # Determine security classification with priority:
                # Watchlist Match > Authorized Person > Unknown Person
                if wl_match and wl_target:
                    # HIGHEST PRIORITY: Watchlist match detected
                    identity_name = wl_target["name"]
                    classification = "Watchlist Match"
                    is_auth = False  # Security classification overrides authorization
                    is_watchlist = True
                    best_score = wl_score
                elif auth_match and auth_target:
                    # Authorized person recognized
                    identity_name = auth_target["name"]
                    classification = "Authorized Person"
                    is_auth = True
                    is_watchlist = False
                    best_score = auth_score
                else:
                    # No match in either registry
                    identity_name = "Unknown"
                    classification = "Unknown Person"
                    is_auth = False
                    is_watchlist = False
                    best_score = max(wl_score, auth_score) if (wl_score or auth_score) else None

                face_obj = {
                    "id": f"face-{idx+1}",
                    "bbox": orig_bbox,
                    "confidence": conf,
                    "identity": identity_name,
                    "classification": classification,
                    "is_authorized": is_auth,
                    "is_watchlist": is_watchlist,
                    "possible_match": is_watchlist,
                    "match_score": best_score,
                }
                faces_payload.append(face_obj)

                detected_entities_this_frame.append({
                    "class": "person",
                    "classification": classification,
                    "bbox": orig_bbox,
                    "confidence": conf,
                    "identity": identity_name,
                    "plate_text": None,
                    "is_authorized": is_auth,
                })

            # -------------------------------------------------------------
            # 2. ANPR Detection (FastALPR + Authorized Vehicle Registry)
            # -------------------------------------------------------------
            if anpr_engine.is_anpr_enabled():
                anpr_result = anpr_engine.process_anpr_frame(
                    infer_frame=infer_frame,
                    source_name=_source_name,
                    orig_w=w,
                    orig_h=h,
                    frame_counter=frame_counter,
                )

                for p in anpr_result.get("confirmed_plates", []):
                    px1, py1, px2, py2 = p["bbox"]
                    plate_bbox = [
                        max(0, int(px1 / infer_scale)),
                        max(0, int(py1 / infer_scale)),
                        min(w, int(px2 / infer_scale)),
                        min(h, int(py2 / infer_scale)),
                    ]
                    plate_text = p.get("plate_text", "")
                    is_auth = p.get("is_authorized", False)
                    classification = p.get("classification", "Unregistered Vehicle")

                    confirmed_plates.append({
                        "id": p.get("id"),
                        "bbox": plate_bbox,
                        "confidence": p["confidence"],
                        "ocr_confidence": p.get("ocr_confidence"),
                        "plate_text": plate_text,
                        "status": "confirmed",
                        "is_authorized": is_auth,
                        "classification": classification,
                        "owner_name": p.get("owner_name", ""),
                    })

                    detected_entities_this_frame.append({
                        "class": "vehicle",
                        "classification": classification,
                        "bbox": plate_bbox,
                        "confidence": p["confidence"],
                        "identity": plate_text,
                        "plate_text": plate_text,
                        "is_authorized": is_auth,
                    })

            # -------------------------------------------------------------
            # 3. Background & Full-Body Person Detection (HOG Detector)
            # -------------------------------------------------------------
            # Detects full bodies of persons in background/perimeters when face is not facing camera or too small
            if _hog_detector is not None and (frame_counter % 2 == 0):
                try:
                    found_rects, weights = _hog_detector.detectMultiScale(
                        infer_frame,
                        winStride=(8, 8),
                        padding=(4, 4),
                        scale=1.05,
                    )
                    for b_idx, rect in enumerate(found_rects):
                        rx, ry, rw, rh = rect
                        hog_weight = float(weights[b_idx]) if b_idx < len(weights) else 0.5
                        if hog_weight < 0.10:
                            continue
                        orig_hog_box = [
                            max(0, int(rx / infer_scale)),
                            max(0, int(ry / infer_scale)),
                            min(w, int((rx + rw) / infer_scale)),
                            min(h, int((ry + rh) / infer_scale)),
                        ]
                        # Check if overlaps with an existing detected face or person
                        overlaps = False
                        for e in detected_entities_this_frame:
                            if e["class"] == "person" and _compute_iou(orig_hog_box, e["bbox"]) > 0.20:
                                overlaps = True
                                break
                        if not overlaps:
                            detected_entities_this_frame.append({
                                "class": "person",
                                "classification": "Unknown Person",
                                "bbox": orig_hog_box,
                                "confidence": min(0.92, round(0.70 + hog_weight * 0.2, 2)),
                                "identity": "Unknown",
                                "plate_text": None,
                                "is_authorized": False,
                            })
                except Exception:
                    pass

            # -------------------------------------------------------------
            # 4. Animal & General Object Detection (Single-Pass Detection)
            # -------------------------------------------------------------
            # Detects animal threats (COCO animal classes) using single-pass detection.
            # Strictly isolates animals from human face recognition.
            if frame_counter % 2 == 0:
                try:
                    obj_dets = model_loader.detect_objects(infer_frame, conf_threshold=0.35)
                    for od in obj_dets:
                        ocls = od.get("class", "").lower()
                        # Strictly process animal classes
                        if ocls in model_loader.COCO_ANIMAL_CLASSES or od.get("classification") == "Potential Animal Threat":
                            obx1, oby1, obx2, oby2 = od["bbox"]
                            orig_anim_box = [
                                max(0, int(obx1 / infer_scale)),
                                max(0, int(oby1 / infer_scale)),
                                min(w, int(obx2 / infer_scale)),
                                min(h, int(oby2 / infer_scale)),
                            ]
                            # Overlap check with existing detections
                            anim_overlaps = False
                            for e in detected_entities_this_frame:
                                if e["class"] == ocls and _compute_iou(orig_anim_box, e["bbox"]) > 0.35:
                                    anim_overlaps = True
                                    break
                            if not anim_overlaps:
                                detected_entities_this_frame.append({
                                    "class": ocls,
                                    "classification": "Potential Animal Threat",
                                    "bbox": orig_anim_box,
                                    "confidence": od.get("confidence", 0.85),
                                    "identity": od.get("identity", ocls.capitalize()),
                                    "plate_text": None,
                                    "is_authorized": False,
                                })
                        elif ocls == "person":
                            obx1, oby1, obx2, oby2 = od["bbox"]
                            orig_p_box = [
                                max(0, int(obx1 / infer_scale)),
                                max(0, int(oby1 / infer_scale)),
                                min(w, int(obx2 / infer_scale)),
                                min(h, int(oby2 / infer_scale)),
                            ]
                            p_overlaps = False
                            for e in detected_entities_this_frame:
                                if e["class"] == "person" and _compute_iou(orig_p_box, e["bbox"]) > 0.25:
                                    p_overlaps = True
                                    break
                            if not p_overlaps:
                                detected_entities_this_frame.append({
                                    "class": "person",
                                    "classification": "Unknown Person",
                                    "bbox": orig_p_box,
                                    "confidence": od.get("confidence", 0.80),
                                    "identity": "Unknown",
                                    "plate_text": None,
                                    "is_authorized": False,
                                })
                except Exception:
                    pass

            # -------------------------------------------------------------
            # 5. Multi-Object Tracking & First-Entry Evidence Association
            # -------------------------------------------------------------
            current_active_entities = []

            for det in detected_entities_this_frame:
                det_bbox = det["bbox"]
                best_track_id = None
                best_iou = 0.0

                for t_id, tr in _tracked_entities.items():
                    iou = _compute_iou(det_bbox, tr["bbox"])
                    if iou > 0.25 and iou > best_iou:
                        best_iou = iou
                        best_track_id = t_id

                if best_track_id is not None:
                    # Update existing track
                    tr = _tracked_entities[best_track_id]
                    tr["bbox"] = det_bbox
                    tr["confidence"] = max(tr["confidence"], det["confidence"])
                    tr["last_seen"] = now_time
                    tr["hits"] += 1
                    tr["classification"] = det["classification"]
                    if det["identity"] != "Unknown":
                        tr["identity"] = det["identity"]
                    if det["plate_text"]:
                        tr["plate_text"] = det["plate_text"]
                    active_track = tr
                else:
                    # First appearance: Lock FIRST-ENTRY IMMUTABLE EVIDENCE BYTES
                    _entity_counter += 1
                    new_track_id = str(_entity_counter)
                    _tracked_entities[new_track_id] = {
                        "track_id": new_track_id,
                        "class": det["class"],
                        "classification": det["classification"],
                        "bbox": det_bbox,
                        "confidence": det["confidence"],
                        "identity": det["identity"],
                        "plate_text": det["plate_text"],
                        "is_authorized": det["is_authorized"],
                        "first_entry_bytes": raw_bytes,  # IMMUTABLE EVIDENCE LOCK
                        "first_entry_time": now_iso,
                        "first_frame_num": frame_counter,
                        "last_seen": now_time,
                        "hits": 1,
                        "alert_fired": False,
                    }
                    active_track = _tracked_entities[new_track_id]
                    logger.info(
                        f"Track #{new_track_id} first appearance captured and secured "
                        f"({det['classification']} @ Frame {frame_counter})"
                    )

                current_active_entities.append(active_track)

            # Cleanup inactive tracks (> 4.0s)
            stale_keys = [k for k, v in _tracked_entities.items() if now_time - v["last_seen"] > 4.0]
            for k in stale_keys:
                del _tracked_entities[k]

            # -------------------------------------------------------------
            # 5. Anomaly Rule Engine & Blockchain Securing
            # -------------------------------------------------------------
            alerts = anomaly_engine.evaluate_anomalies("CAM-01", current_active_entities, zones)

            for alert in alerts:
                t_id = alert["track_id"]
                tr = _tracked_entities.get(t_id)

                if tr and not tr.get("alert_fired"):
                    tr["alert_fired"] = True
                    event_id = f"EVT-{uuid.uuid4().hex[:6].upper()}"

                    # Retrieve IMMUTABLE first-entry image bytes
                    first_entry_bytes = tr.get("first_entry_bytes") or raw_bytes
                    first_entry_time = tr.get("first_entry_time") or now_iso

                    event_payload = {
                        "event_id": event_id,
                        "timestamp": first_entry_time,
                        "camera_id": "CAM-01",
                        "track_id": t_id,
                        "event_type": alert["event_type"],
                        "classification": alert["classification"],
                        "zone_name": alert["zone_name"],
                        "confidence": alert["confidence"],
                        "severity": alert["severity"],
                        "description": alert["description"],
                    }

                    # Secure on Tamper-Proof Blockchain Ledger
                    bc_res = blockchain.record_security_event_blockchain(
                        event_id=event_id,
                        event_data=event_payload,
                        evidence_bytes=first_entry_bytes,
                        camera_id="CAM-01",
                    )

                    # Dispatch Alert to Officer Panel
                    officer_alert = {
                        "id": event_id,
                        "time": first_entry_time,
                        "camera_id": "CAM-01",
                        "camera_name": "Perimeter Cam 01",
                        "event_type": alert["event_type"],
                        "classification": alert["classification"],
                        "zone_name": alert["zone_name"],
                        "track_id": t_id,
                        "severity": alert["severity"],
                        "confidence": alert["confidence"],
                        "description": alert["description"],
                        "snapshot_path": f"/api/evidence/{event_id}.jpg",
                        "evidence_hash": bc_res["block"]["evidence_hash"],
                        "event_hash": bc_res["block"]["metadata_hash"],
                        "block_id": bc_res["block"]["block_number"],
                        "status": "Active",
                        "metadata": alert["metadata"],
                    }
                    storage.add_alert(officer_alert)
                    alert_store.add_alert(officer_alert)

                    logger.info(
                        f"SECURITY ALERT RAISED: {alert['event_type']} (Track #{t_id}) "
                        f"anchored in Blockchain Block #{bc_res['block']['block_number']}"
                    )

            # Update Detection Cache atomically
            with _detection_lock:
                _latest_faces = faces_payload
                _latest_confirmed_plates = confirmed_plates
                _latest_entities = current_active_entities

            # Compute inference FPS
            now_inf = time.time()
            if now_inf - infer_t0 >= 1.0:
                _inference_fps = infer_count / (now_inf - infer_t0)
                infer_count = 0
                infer_t0 = now_inf

        except Exception as e:
            logger.warning(f"AI Worker loop exception: {e}")

        time.sleep(0.01)


# --- Visual Tactical Surveillance Overlay ---

def _draw_surveillance_overlay(frame, faces, confirmed_plates, entities, source_title, disp_scale):
    """Draws clean, intentional detection annotations without debug HUD text or ugly abbreviations."""
    if not _has_cv2 or frame is None:
        return

    h, w = frame.shape[:2]

    # Draw Classified Entity Bounding Boxes and Clean Badges
    for e in entities:
        bbox = e.get("bbox")
        if not bbox or len(bbox) < 4:
            continue
        ox1, oy1, ox2, oy2 = bbox
        x1 = max(0, min(w - 1, int(ox1 * disp_scale)))
        y1 = max(0, min(h - 1, int(oy1 * disp_scale)))
        x2 = max(x1 + 1, min(w, int(ox2 * disp_scale)))
        y2 = max(y1 + 1, min(h, int(oy2 * disp_scale)))

        cls_type = e.get("classification", "Unknown Person")
        ident = str(e.get("identity") or "Unknown")
        tid = str(e.get("track_id") or "0")
        conf = int(e.get("confidence", 0.85) * 100)

        # Standardized professional security classifications
        if cls_type == "Watchlist Match":
            color = (60, 20, 220)       # High-Alert Magenta/Red (BGR)
            badge = f"\xe2\x9a\xa0 WATCHLIST: {ident.upper()} [{conf}%]"
            text_color = (255, 255, 255)
        elif cls_type == "Authorized Person":
            color = (36, 179, 57)       # Professional Green (BGR)
            badge = f"AUTHORIZED PERSON: {ident.upper()} [{conf}%]"
            text_color = (255, 255, 255)
        elif cls_type == "Unknown Person":
            color = (38, 38, 230)       # Alert Red (BGR)
            badge = f"UNKNOWN PERSON #{tid} [{conf}%]"
            text_color = (255, 255, 255)
        elif cls_type == "Authorized Vehicle":
            color = (201, 185, 22)      # Cyan / Turquoise (BGR)
            badge = f"AUTHORIZED VEHICLE #{tid}: {ident.upper()}"
            text_color = (0, 0, 0)
        elif cls_type == "Unregistered Vehicle":
            color = (38, 140, 245)      # Amber Alert (BGR)
            badge = f"UNREGISTERED VEHICLE #{tid}: {ident.upper()}"
            text_color = (255, 255, 255)
        elif cls_type in ("Potential Animal Threat", "Animal"):
            color = (30, 30, 220)       # Crimson Alert (BGR)
            animal_label = ident.upper() if ident and ident != "UNKNOWN" else e.get("class", "ANIMAL").upper()
            badge = f"ANIMAL THREAT: {animal_label} [{conf}%]"
            text_color = (255, 255, 255)
        else:
            color = (38, 38, 230)       # Alert Red fallback for unclassified person (NEVER animal)
            badge = f"UNKNOWN PERSON #{tid} [{conf}%]"
            text_color = (255, 255, 255)

        # Bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Subtle corner brackets
        corner_len = min(16, max(6, (x2 - x1) // 5))
        cv2.line(frame, (x1, y1), (x1 + corner_len, y1), color, 3)
        cv2.line(frame, (x1, y1), (x1, y1 + corner_len), color, 3)
        cv2.line(frame, (x2, y1), (x2 - corner_len, y1), color, 3)
        cv2.line(frame, (x2, y1), (x2, y1 + corner_len), color, 3)
        cv2.line(frame, (x1, y2), (x1 + corner_len, y2), color, 3)
        cv2.line(frame, (x1, y2), (x1, y2 - corner_len), color, 3)
        cv2.line(frame, (x2, y2), (x2 - corner_len, y2), color, 3)
        cv2.line(frame, (x2, y2), (x2, y2 - corner_len), color, 3)

        # Badge banner with background padding
        font_scale = 0.38
        thickness = 1
        (tw, th), _ = cv2.getTextSize(badge, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        bw = tw + 10
        bh = th + 8
        by1 = max(0, y1 - bh)
        by2 = y1

        cv2.rectangle(frame, (x1, by1), (x1 + bw, by2), color, -1)
        cv2.putText(
            frame,
            badge,
            (x1 + 5, by2 - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            text_color,
            thickness,
            cv2.LINE_AA,
        )


def _compute_iou(boxA: list, boxB: list) -> float:
    """Computes Intersection-over-Union safely for coordinate lists."""
    try:
        xA = max(float(boxA[0]), float(boxB[0]))
        yA = max(float(boxA[1]), float(boxB[1]))
        xB = min(float(boxA[2]), float(boxB[2]))
        yB = min(float(boxA[3]), float(boxB[3]))
        inter = max(0.0, xB - xA) * max(0.0, yB - yA)
        areaA = max(1.0, (float(boxA[2]) - float(boxA[0])) * (float(boxA[3]) - float(boxA[1])))
        areaB = max(1.0, (float(boxB[2]) - float(boxB[0])) * (float(boxB[3]) - float(boxB[1])))
        return float(inter) / float(areaA + areaB - inter)
    except Exception:
        return 0.0


def _draw_status_card(title, message, color=(22, 185, 201)):
    if _has_cv2:
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (8, 14, 22)
        cv2.rectangle(img, (20, 20), (620, 460), (20, 32, 46), 1)
        cv2.putText(img, "IBVAP AUTONOMOUS SURVEILLANCE NODE", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 130, 160), 1)
        cv2.putText(img, title, (40, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color[::-1], 2)
        cv2.putText(img, message, (40, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 200, 220), 1)
        cv2.putText(img, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), (40, 430),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (70, 95, 120), 1)
        _, jpeg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return jpeg.tobytes()
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444"
        b"\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01"
        b"\x11\x00\xff\xda\x00\x08\x01\x01\x00\x00?\x00T\xdb\x9e\xa3"
        b"\x13\xa0\x00\x1c\xff\xd9"
    )


# Backward-compatible helper used by test scripts
def _handle_possible_match_alert(name, score, face_id, evidence_bytes=None):
    return _handle_match_alert(name, score, face_id, evidence_bytes)


def _handle_match_alert(name, score, face_id, evidence_bytes=None):
    """Rate-limited alert for real watchlist matches."""
    global _last_alert_time
    now_t = time.time()
    last_t = _last_alert_time.get(name, 0.0)

    if now_t - last_t > 5.0:
        _last_alert_time[name] = now_t
        alert_id = f"alert-{uuid.uuid4().hex[:6]}"
        now_iso = datetime.utcnow().isoformat() + "Z"

        alert_obj = {
            "id": alert_id,
            "time": now_iso,
            "event_type": "WATCHLIST_MATCH",
            "type": "WATCHLIST_MATCH",
            "severity": "HIGH",
            "level": "HIGH",
            "description": f"Watchlist match detected: {name} (Similarity: {score})",
            "message": f"Watchlist match detected: {name} (Similarity: {score})",
            "evidence_saved": True,
        }
        alert_store.add_alert(alert_obj)

        meta = {"target": name, "similarity": score, "face_id": face_id}
        ledger.record_evidence_event(
            event_type="fcr_match",
            source_name=_source_name,
            evidence_jpeg_bytes=evidence_bytes,
            metadata=meta,
        )
        fcr_watchlist.log_match({"time": now_iso, "name": name, "score": score, "face_id": face_id})
