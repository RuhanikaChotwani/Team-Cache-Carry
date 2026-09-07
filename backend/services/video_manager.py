"""Video Manager Service for IBVAP.
Handles bundled sample demo video discovery and secure user video uploads.
No synthetic video generation or fake frames are created.
"""

import os
import uuid
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SAMPLE_VIDEOS_DIR = Path(__file__).resolve().parent.parent / "sample_videos"
RUNTIME_UPLOADS_DIR = Path(__file__).resolve().parent.parent / "runtime_uploads"
MANIFEST_FILE = SAMPLE_VIDEOS_DIR / "manifest.json"

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB

# In-memory registry of uploaded videos in the current session: video_id -> metadata
_uploaded_videos_registry: Dict[str, dict] = {}


def _ensure_directories():
    SAMPLE_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    # If sample_videos is empty, seed from available uploads so demo mode works out-of-the-box
    existing_samples = [f for f in SAMPLE_VIDEOS_DIR.iterdir() if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS]
    if not existing_samples and RUNTIME_UPLOADS_DIR.exists():
        upload_files = [f for f in sorted(RUNTIME_UPLOADS_DIR.iterdir(), key=lambda x: x.stat().st_size) if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS]
        if upload_files:
            try:
                target_veh = SAMPLE_VIDEOS_DIR / "vehicle_checkpoint.mp4"
                if not target_veh.exists():
                    shutil.copy2(upload_files[0], target_veh)

                if len(upload_files) > 1:
                    target_perim = SAMPLE_VIDEOS_DIR / "perimeter_patrol.mp4"
                    if not target_perim.exists():
                        shutil.copy2(upload_files[-1], target_perim)

                if not MANIFEST_FILE.exists():
                    manifest_content = [
                        {
                            "filename": "vehicle_checkpoint.mp4",
                            "name": "Border Checkpoint FastALPR Feed",
                            "description": "Vehicle surveillance with ANPR and license plate recognition."
                        },
                        {
                            "filename": "perimeter_patrol.mp4",
                            "name": "Perimeter Patrol Optical Feed",
                            "description": "Multi-target person detection and perimeter surveillance."
                        }
                    ]
                    with open(MANIFEST_FILE, "w", encoding="utf-8") as mf:
                        json.dump(manifest_content, mf, indent=2)
            except Exception:
                pass


def list_demo_videos() -> dict:
    """Returns available bundled demo videos from backend/sample_videos/.
    Returns empty list with truthful message if no videos exist.
    """
    _ensure_directories()

    manifest_map = {}
    if MANIFEST_FILE.exists():
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
                if isinstance(manifest_data, list):
                    for item in manifest_data:
                        if isinstance(item, dict) and "filename" in item:
                            manifest_map[item["filename"]] = item
        except Exception:
            manifest_map = {}

    videos = []
    for file_path in sorted(SAMPLE_VIDEOS_DIR.iterdir()):
        if file_path.is_file() and file_path.suffix.lower() in ALLOWED_EXTENSIONS:
            filename = file_path.name
            file_id = file_path.stem

            if filename in manifest_map:
                meta = manifest_map[filename]
                display_name = meta.get("name", file_id.replace("_", " ").title())
                description = meta.get("description", "Bundled sample surveillance video.")
            else:
                display_name = file_id.replace("_", " ").title()
                description = f"Sample video clip: {filename}"

            videos.append({
                "id": file_id,
                "name": display_name,
                "filename": filename,
                "description": description,
                "size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
            })

    if not videos:
        return {
            "videos": [],
            "message": "No demo videos found. Add an MP4 to backend/sample_videos/ or upload one.",
        }

    return {
        "videos": videos,
        "message": f"Found {len(videos)} demo video(s).",
    }


def save_uploaded_video(original_filename: str, file_bytes: bytes) -> dict:
    """Securely validates and stores an uploaded surveillance video.
    Uses UUID-based filenames to prevent path traversal and script execution.
    """
    _ensure_directories()

    if not original_filename:
        raise ValueError("Filename is required.")

    # 1. Validate file size
    file_size = len(file_bytes)
    if file_size == 0:
        raise ValueError("Uploaded file is empty.")
    if file_size > MAX_UPLOAD_SIZE_BYTES:
        raise ValueError(f"File size ({round(file_size / (1024*1024), 1)} MB) exceeds 100 MB limit.")

    # 2. Validate file extension
    clean_name = os.path.basename(original_filename)
    ext = Path(clean_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(f"Unsupported file format '{ext}'. Allowed formats: {allowed_list}")

    # 3. Generate safe UUID storage filename
    video_id = f"upl_{uuid.uuid4().hex[:12]}"
    safe_filename = f"{video_id}{ext}"
    target_path = RUNTIME_UPLOADS_DIR / safe_filename

    # 4. Write bytes to disk
    with open(target_path, "wb") as f:
        f.write(file_bytes)

    display_name = Path(clean_name).stem.replace("_", " ").replace("-", " ").strip()
    if not display_name:
        display_name = "Uploaded Video"

    metadata = {
        "id": video_id,
        "name": display_name,
        "original_filename": clean_name,
        "safe_filename": safe_filename,
        "size_mb": round(file_size / (1024 * 1024), 2),
        "disk_path": str(target_path),
    }

    _uploaded_videos_registry[video_id] = metadata

    return {
        "id": video_id,
        "name": display_name,
        "filename": clean_name,
        "size_mb": metadata["size_mb"],
    }


def get_video_by_id(video_id: str) -> Optional[dict]:
    """Retrieves metadata and validated filepath for a demo/sample video by ID or filename."""
    _ensure_directories()
    if not video_id:
        return None

    vid_str = str(video_id).strip()
    if SAMPLE_VIDEOS_DIR.exists():
        for f in sorted(SAMPLE_VIDEOS_DIR.iterdir()):
            if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS:
                if (
                    f.stem == vid_str
                    or f.name == vid_str
                    or f.stem.lower() == vid_str.lower()
                    or f.name.lower() == vid_str.lower()
                ):
                    return {
                        "id": f.stem,
                        "name": f.stem.replace("_", " ").title(),
                        "filename": f.name,
                        "path": str(f.resolve()),
                        "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                    }
    return None


def get_uploaded_video_by_id(video_id: str) -> Optional[dict]:
    """Retrieves metadata and validated filepath for an uploaded video by ID or filename."""
    _ensure_directories()
    if not video_id:
        return None

    vid_str = str(video_id).strip()

    # 1. In-memory registry
    if vid_str in _uploaded_videos_registry:
        meta = _uploaded_videos_registry[vid_str]
        path = meta.get("disk_path")
        if path and os.path.exists(path):
            return {
                "id": meta["id"],
                "name": meta["name"],
                "filename": meta.get("original_filename", os.path.basename(path)),
                "path": str(Path(path).resolve()),
                "size_mb": meta.get("size_mb", 0.0),
            }

    for k, meta in _uploaded_videos_registry.items():
        if k.lower() == vid_str.lower():
            path = meta.get("disk_path")
            if path and os.path.exists(path):
                return {
                    "id": meta["id"],
                    "name": meta["name"],
                    "filename": meta.get("original_filename", os.path.basename(path)),
                    "path": str(Path(path).resolve()),
                    "size_mb": meta.get("size_mb", 0.0),
                }

    # 2. Check disk in RUNTIME_UPLOADS_DIR
    if RUNTIME_UPLOADS_DIR.exists():
        for f in sorted(RUNTIME_UPLOADS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS:
                if (
                    f.name == vid_str
                    or f.stem == vid_str
                    or f.name.lower() == vid_str.lower()
                    or f.stem.lower() == vid_str.lower()
                    or vid_str in f.name
                ):
                    return {
                        "id": f.stem,
                        "name": f.stem.replace("_", " ").title(),
                        "filename": f.name,
                        "path": str(f.resolve()),
                        "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                    }

    # 3. Direct absolute or relative path
    candidate = Path(vid_str)
    if candidate.exists() and candidate.is_file():
        return {
            "id": candidate.stem,
            "name": candidate.stem.replace("_", " ").title(),
            "filename": candidate.name,
            "path": str(candidate.resolve()),
            "size_mb": round(candidate.stat().st_size / (1024 * 1024), 2),
        }

    return None


def list_uploaded_videos() -> dict:
    """Returns all available uploaded videos in RUNTIME_UPLOADS_DIR."""
    _ensure_directories()
    videos = []
    if RUNTIME_UPLOADS_DIR.exists():
        for f in sorted(RUNTIME_UPLOADS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS:
                meta = _uploaded_videos_registry.get(f.stem, {})
                display_name = meta.get("name") or f.stem.replace("_", " ").title()
                orig_name = meta.get("original_filename") or f.name
                videos.append({
                    "id": f.stem,
                    "name": display_name,
                    "filename": orig_name,
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                    "path": str(f.resolve()),
                })
    return {
        "videos": videos,
        "message": f"Found {len(videos)} uploaded video(s).",
    }


def get_all_video_sources() -> dict:
    """Returns combined demo and uploaded video sources for UI dropdowns."""
    demo = list_demo_videos()
    uploaded = list_uploaded_videos()
    return {
        "demo_videos": demo.get("videos", []),
        "uploaded_videos": uploaded.get("videos", []),
        "videos": demo.get("videos", []),
    }


def resolve_video_path(source_type: str, source_id_or_path: Optional[str]) -> Tuple[Optional[str], str]:
    """Resolves a source_type and identifier/path to a safe, validated absolute filepath and display name.
    Never allows arbitrary directory traversal.
    """
    _ensure_directories()

    if not source_id_or_path:
        return None, "Unknown Video"

    str_input = str(source_id_or_path).strip()

    # 1. Check if source_id is in uploaded registry (exact or lowercase)
    if str_input in _uploaded_videos_registry:
        meta = _uploaded_videos_registry[str_input]
        path = meta["disk_path"]
        if os.path.exists(path):
            return path, meta["name"]

    for k, meta in _uploaded_videos_registry.items():
        if k.lower() == str_input.lower():
            path = meta["disk_path"]
            if os.path.exists(path):
                return path, meta["name"]

    # 2. Check if file is in RUNTIME_UPLOADS_DIR by safe filename or stem
    if RUNTIME_UPLOADS_DIR.exists():
        for f in RUNTIME_UPLOADS_DIR.iterdir():
            if f.is_file() and (
                f.name == str_input
                or f.stem == str_input
                or f.name.lower() == str_input.lower()
                or f.stem.lower() == str_input.lower()
            ):
                return str(f), f.stem.replace("_", " ").title()

    # 3. Check if file is in SAMPLE_VIDEOS_DIR by filename or stem
    if SAMPLE_VIDEOS_DIR.exists():
        for f in SAMPLE_VIDEOS_DIR.iterdir():
            if f.is_file() and (
                f.name == str_input
                or f.stem == str_input
                or f.name.lower() == str_input.lower()
                or f.stem.lower() == str_input.lower()
            ):
                return str(f), f.stem.replace("_", " ").title()

    # 4. Check if sanitized relative path within sample_videos or runtime_uploads
    base_name = os.path.basename(str_input)
    candidate_sample = SAMPLE_VIDEOS_DIR / base_name
    if candidate_sample.exists() and candidate_sample.is_file():
        return str(candidate_sample), candidate_sample.stem.replace("_", " ").title()

    candidate_upload = RUNTIME_UPLOADS_DIR / base_name
    if candidate_upload.exists() and candidate_upload.is_file():
        return str(candidate_upload), candidate_upload.stem.replace("_", " ").title()

    # 5. Check if direct absolute path exists within project
    if os.path.isabs(str_input) and os.path.exists(str_input) and os.path.isfile(str_input):
        return str_input, Path(str_input).stem.replace("_", " ").title()

    return None, str_input
