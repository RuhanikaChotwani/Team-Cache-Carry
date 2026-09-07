"""IBVAP Backend - Main FastAPI Application Entry Point.
Intelligent Border Video Analytics Platform.
Features:
- Authentication & RBAC (Admin & Security Officer)
- Live CCTV & FastALPR (Authorized vs Unregistered Vehicles)
- FCR Surveillance (Authorized vs Unknown Person)
- Animal Threat Detection & Anomaly Rule Engine
- First-Entry Evidence Image Preservation
- Tamper-Proof Blockchain Ledger with Forensic Backend Verification
- High-Framerate Decoupled MJPEG Streaming
"""

import os
from pathlib import Path
from typing import Optional, Union, List
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, Response
from pydantic import BaseModel

from services import (
    webcam,
    fcr_watchlist,
    fcr_authorized_faces,
    anpr_engine,
    anpr_store,
    alert_store,
    ledger,
    face_engine,
    video_manager,
    storage,
    blockchain,
    auth,
    anomaly_engine,
)

app = FastAPI(
    title="IBVAP - Intelligent Border Video Analytics Platform",
    version="2.5.0",
    description="Defense-grade Border Surveillance Platform with Face Recognition, ANPR, Blockchain Evidence Integrity, and Anomaly Engine.",
)

# CORS - allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Request Models ---

class StartStreamRequest(BaseModel):
    source_type: str = "webcam"
    source_id: Optional[str] = None
    source: Optional[Union[int, str]] = None
    source_name: Optional[str] = None
    loop: bool = True


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthorizedVehicleCreate(BaseModel):
    plate_number: str
    vehicle_type: str = "Car"
    owner_name: str = ""
    authorized_by: str = "Command"


class AuthorizedPersonCreate(BaseModel):
    name: str
    role_type: str = "Authorized"
    badge_id: str = ""
    face_id: str = ""
    department: str = "Border Security Force"


class ZoneCreateRequest(BaseModel):
    name: str
    points: list
    severity: str = "Critical"
    camera_id: str = "cam-01"


# =========================================================
# 1. AUTHENTICATION & ACCESS CONTROL
# =========================================================

@app.post("/api/auth/login")
def login(creds: LoginRequest):
    user = storage.get_user(creds.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Check username or password.",
        )

    if not auth.verify_password(creds.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Check username or password.",
        )

    token = auth.create_access_token({
        "sub": user["username"],
        "role": user["role"],
        "name": user["full_name"],
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "full_name": user["full_name"],
        }
    }


@app.get("/api/auth/me")
def get_current_user_profile(current_user: dict = Depends(auth.get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "role": current_user["role"],
        "full_name": current_user["full_name"],
    }


@app.post("/api/auth/logout")
def logout():
    return {"status": "logged_out", "message": "Session terminated successfully."}


# =========================================================
# 2. SYSTEM HEALTH & TELEMETRY
# =========================================================

@app.get("/api/health")
def health():
    f_status = face_engine.get_face_engine_status() or {}
    a_status = anpr_engine.get_status() or {}
    w_status = webcam.get_status() or {}

    return {
        "status": "operational",
        "service": "IBVAP Intelligent Border Surveillance Platform",
        "version": "2.5.0",
        "models": {
            "yunet": {
                "name": "YuNet Face Detector (2023mar)",
                "path": f_status.get("yunet_path"),
                "file_exists": f_status.get("yunet_file_exists", False),
                "loaded": f_status.get("yunet_loaded", False),
                "error": f_status.get("yunet_error"),
            },
            "sface": {
                "name": "SFace Face Recognizer (2021dec)",
                "path": f_status.get("sface_path"),
                "file_exists": f_status.get("sface_file_exists", False),
                "loaded": f_status.get("sface_loaded", False),
                "error": f_status.get("sface_error"),
            },
            "fast_alpr": {
                "name": "FastALPR (YOLO-v9-t + CCT-XS-v2)",
                "loaded": a_status.get("alpr_loaded", False),
                "error": a_status.get("alpr_error"),
            },
        },
        "camera": w_status,
        "database": {
            "authorized_vehicles": storage.count_table("authorized_vehicles"),
            "authorized_personnel": storage.count_table("authorized_personnel"),
            "total_alerts": storage.count_table("alerts"),
            "blockchain_blocks": len(storage.get_blockchain()),
        }
    }


# =========================================================
# 3. LIVE STREAMING & DECOUPLED CAPTURE
# =========================================================

@app.post("/api/webcam/start")
def start_webcam(
    body: Optional[StartStreamRequest] = Body(None),
    source: Optional[Union[int, str]] = None,
):
    if body is not None:
        return webcam.start(
            source=body.source if body.source is not None else (body.source_id or 0),
            source_type=body.source_type,
            source_id=body.source_id,
            source_name=body.source_name,
            loop=body.loop,
        )
    src_val = source if source is not None else 0
    return webcam.start(source=src_val, source_type="webcam")


@app.post("/api/webcam/stop")
def stop_webcam():
    return webcam.stop()


@app.get("/api/webcam/status")
def webcam_status():
    return webcam.get_status()


@app.get("/api/webcam/raw.mjpg")
def webcam_raw_stream(session: Optional[int] = None):
    return StreamingResponse(
        webcam.raw_mjpeg_generator(session_id=session),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/api/webcam/ai.mjpg")
def webcam_ai_stream(session: Optional[int] = None):
    return StreamingResponse(
        webcam.ai_mjpeg_generator(session_id=session),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/api/webcam/detections")
def webcam_detections():
    return webcam.get_detections_payload()


@app.get("/api/webcam/debug-face-frame.jpg")
def webcam_debug_face_frame():
    return Response(
        content=webcam.get_debug_face_frame(),
        media_type="image/jpeg",
    )


# =========================================================
# 4. VIDEO SOURCE MANAGEMENT & UPLOAD
# =========================================================

@app.get("/api/video-sources")
def get_video_sources():
    return video_manager.get_all_video_sources()


@app.post("/api/video/upload")
async def upload_video(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        res = video_manager.save_uploaded_video(file.filename or "uploaded_video.mp4", file_bytes)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


# =========================================================
# 5. FCR WATCHLIST & AUTHORIZED PERSONNEL
# =========================================================

@app.post("/api/fcr/enroll")
async def enroll_face(
    name: str = Form(...),
    image: UploadFile = File(...),
    left_image: Optional[UploadFile] = File(None),
    right_image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(auth.get_current_user),
):
    """Enroll a Person of Interest on the Watchlist.
    Requires a front-facing face image. Optionally accepts left/right profile images
    for improved multi-angle recognition.
    NOTE: This does NOT add the person to Authorized Personnel.
    Watchlist and Authorized Personnel are independent registries.
    """
    try:
        image_bytes = await image.read()
        left_bytes = await left_image.read() if left_image else None
        right_bytes = await right_image.read() if right_image else None
        res = fcr_watchlist.enroll_target_image(
            name=name,
            image_bytes=image_bytes,
            left_image_bytes=left_bytes,
            right_image_bytes=right_bytes,
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enrollment failed: {e}")


@app.get("/api/fcr/watchlist")
def get_watchlist():
    return fcr_watchlist.get_watchlist()


@app.delete("/api/fcr/watchlist/{face_id}")
def delete_watchlist_face(face_id: str, current_user: dict = Depends(auth.get_current_user)):
    """Delete a Person of Interest from the Watchlist.
    Does NOT affect the Authorized Personnel registry.
    """
    success = fcr_watchlist.delete_from_watchlist(face_id)
    if not success:
        raise HTTPException(status_code=404, detail="Face record not found")
    return {"status": "deleted", "id": face_id}


@app.get("/api/fcr/matches")
def get_recent_matches():
    return fcr_watchlist.get_recent_matches()


@app.get("/api/authorized-personnel")
def list_authorized_personnel():
    return storage.get_authorized_personnel()


@app.post("/api/authorized-personnel")
def add_authorized_personnel(data: AuthorizedPersonCreate, current_user: dict = Depends(auth.get_current_user)):
    return storage.add_authorized_person(
        name=data.name,
        role_type=data.role_type,
        badge_id=data.badge_id,
        face_id=data.face_id,
        department=data.department
    )


@app.post("/api/authorized-personnel/enroll-face")
async def enroll_authorized_face(
    name: str = Form(...),
    role_type: str = Form("Security Officer"),
    badge_id: str = Form(""),
    department: str = Form("Border Security Force"),
    image: UploadFile = File(...),
    left_image: Optional[UploadFile] = File(None),
    right_image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(auth.get_current_user),
):
    """Enroll a face for Authorized Personnel recognition with full metadata.
    Requires a front-facing face image. Optionally accepts left/right profile images.
    This is SEPARATE from the Watchlist — enrolling here does NOT add the person
    to the Persons of Interest watchlist.
    """
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Personnel Full Name & Rank is required.")

    try:
        image_bytes = await image.read()
        left_bytes = await left_image.read() if left_image else None
        right_bytes = await right_image.read() if right_image else None
        res = fcr_authorized_faces.enroll_authorized_face(
            name=name.strip(),
            image_bytes=image_bytes,
            left_image_bytes=left_bytes,
            right_image_bytes=right_bytes,
        )
        face_id = res.get("id", "")
        # Register or update in the authorized_personnel SQLite table
        existing_auth, existing_rec = storage.is_person_authorized(name)
        if existing_auth and existing_rec:
            storage.update_authorized_person(
                person_id=existing_rec["id"],
                face_id=face_id,
                role_type=role_type,
                badge_id=badge_id,
                department=department
            )
            res["personnel_id"] = existing_rec["id"]
        else:
            p_rec = storage.add_authorized_person(
                name=name.strip(),
                role_type=role_type,
                badge_id=badge_id,
                face_id=face_id,
                department=department
            )
            res["personnel_id"] = p_rec.get("id")
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authorized face enrollment failed: {e}")


@app.post("/api/authorized-personnel/{person_id}/face")
async def update_personnel_face(
    person_id: str,
    image: UploadFile = File(...),
    left_image: Optional[UploadFile] = File(None),
    right_image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(auth.get_current_user),
):
    """Update or add face biometrics for an existing authorized personnel member."""
    person = storage.get_authorized_person_by_id(person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Authorized personnel record not found")

    try:
        image_bytes = await image.read()
        left_bytes = await left_image.read() if left_image else None
        right_bytes = await right_image.read() if right_image else None

        res = fcr_authorized_faces.enroll_authorized_face(
            name=person["name"],
            image_bytes=image_bytes,
            left_image_bytes=left_bytes,
            right_image_bytes=right_bytes,
            face_id=person.get("face_id"),
        )
        storage.update_authorized_person(person_id, face_id=res.get("id", ""))
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update personnel face biometrics: {e}")


@app.get("/api/authorized-personnel/faces")
def list_authorized_faces():
    """Returns all enrolled authorized personnel face entries with embeddings."""
    faces = fcr_authorized_faces.get_authorized_faces()
    # Return without raw embeddings for API response size
    return [{
        "id": f.get("id"),
        "name": f.get("name"),
        "confidence": f.get("confidence"),
        "thumbnail": f.get("thumbnail"),
        "embedding_count": len(f.get("embeddings", [f.get("embedding")])),
        "created_at": f.get("created_at"),
    } for f in faces]


@app.delete("/api/authorized-personnel/faces/{face_id}")
def delete_authorized_face(face_id: str, current_user: dict = Depends(auth.get_current_user)):
    """Delete an authorized personnel face entry."""
    success = fcr_authorized_faces.delete_authorized_face(face_id)
    if not success:
        raise HTTPException(status_code=404, detail="Authorized face record not found")
    return {"status": "deleted", "id": face_id}


@app.delete("/api/authorized-personnel/{person_id}")
def delete_authorized_personnel(person_id: str, current_user: dict = Depends(auth.get_current_user)):
    success = storage.delete_authorized_person(person_id)
    if not success:
        raise HTTPException(status_code=404, detail="Personnel record not found")
    return {"status": "deleted", "id": person_id}


# =========================================================
# 6. ANPR & AUTHORIZED VEHICLES
# =========================================================

@app.get("/api/anpr/latest")
def get_latest_anpr():
    return anpr_engine.get_latest_anpr()


@app.get("/api/anpr/diagnostics")
def get_anpr_diagnostics():
    return anpr_engine.get_diagnostics()


@app.post("/api/anpr/toggle")
def toggle_anpr(body: dict = Body(...), current_user: dict = Depends(auth.get_current_user)):
    enabled = body.get("enabled", True)
    anpr_engine.set_anpr_enabled(enabled)
    return {"status": "updated", "anpr_enabled": anpr_engine.is_anpr_enabled()}


@app.get("/api/anpr/records")
def get_anpr_records(limit: int = 100):
    return anpr_store.get_records(limit=limit)


@app.delete("/api/anpr/records")
def clear_anpr_records(current_user: dict = Depends(auth.get_current_user)):
    return anpr_store.clear_records()


@app.get("/api/authorized-vehicles")
def list_authorized_vehicles():
    return storage.get_authorized_vehicles()


@app.post("/api/authorized-vehicles")
def add_authorized_vehicle_endpoint(data: AuthorizedVehicleCreate, current_user: dict = Depends(auth.get_current_user)):
    return storage.add_authorized_vehicle(
        plate_number=data.plate_number,
        vehicle_type=data.vehicle_type,
        owner_name=data.owner_name,
        authorized_by=data.authorized_by,
    )


@app.delete("/api/authorized-vehicles/{plate_number}")
def delete_authorized_vehicle_endpoint(plate_number: str, current_user: dict = Depends(auth.get_current_user)):
    success = storage.delete_authorized_vehicle(plate_number)
    if not success:
        raise HTTPException(status_code=404, detail="Vehicle plate not found in authorized registry")
    return {"status": "deleted", "plate_number": plate_number}


# =========================================================
# 7. SECURITY ALERTS & OFFICER PANEL ENDPOINTS
# =========================================================

@app.get("/api/alerts")
def get_alerts(limit: int = 100):
    return alert_store.get_alerts(limit=limit)


@app.delete("/api/alerts")
def clear_alerts(current_user: dict = Depends(auth.get_current_user)):
    storage.clear_alerts()
    return alert_store.clear_alerts()


@app.get("/api/officer/alerts")
def get_officer_alerts(limit: int = 100, current_user: dict = Depends(auth.get_current_user)):
    """Returns security incidents with first-entry snapshot evidence links,
    tamper-proof hashes, and blockchain anchor status.
    Protected endpoint: Officer or Admin credentials required.
    """
    records = storage.get_all_evidence_records(limit=limit)
    if not records:
        # Fallback to storage.get_alerts if evidence records table was seeded from alerts
        return storage.get_alerts(limit=limit)
    return records


# =========================================================
# 8. EVIDENCE ACCESS, DOWNLOAD & FORENSIC VERIFICATION
# =========================================================

@app.get("/api/evidence/{filename}")
def get_evidence_image(filename: str):
    """Serves the exact, immutable first-entry JPEG evidence from disk."""
    evidence_path = blockchain.EVIDENCE_DIR / filename
    if not evidence_path.exists():
        raise HTTPException(status_code=404, detail=f"Evidence file '{filename}' not found.")
    return FileResponse(
        path=str(evidence_path),
        media_type="image/jpeg",
        filename=filename,
    )


@app.get("/api/evidence/{event_id}/download")
def download_evidence_image(event_id: str, current_user: dict = Depends(auth.get_current_user)):
    """Officer Download Endpoint: Forces browser download of the exact first-entry evidence image.
    Protected: Requires authenticated officer session.
    """
    filename = f"{event_id}.jpg"
    evidence_path = blockchain.EVIDENCE_DIR / filename
    if not evidence_path.exists():
        # Fallback to any matching file in evidence directory
        found = list(blockchain.EVIDENCE_DIR.glob(f"*{event_id}*"))
        if found:
            evidence_path = found[0]
            filename = evidence_path.name
        else:
            raise HTTPException(status_code=404, detail=f"Evidence for event '{event_id}' not found.")

    return FileResponse(
        path=str(evidence_path),
        media_type="image/jpeg",
        filename=f"EVIDENCE_{filename}",
        headers={"Content-Disposition": f'attachment; filename="EVIDENCE_{filename}"'}
    )


@app.get("/api/evidence/{event_id}/verify")
def verify_evidence_endpoint(event_id: str, current_user: dict = Depends(auth.get_current_user)):
    """Forensic Backend Verification Endpoint:
    Loads stored event and image bytes, computes current SHA-256 hashes,
    and compares against the immutable blockchain block.
    Protected: Requires authenticated officer session.
    """
    return blockchain.verify_event_integrity(event_id)


@app.get("/api/evidence/{event_id}/certificate")
def get_certificate_endpoint(event_id: str, current_user: dict = Depends(auth.get_current_user)):
    """Generates official verification certificate for audited court/chain of custody records.
    Protected: Requires authenticated officer session.
    """
    cert = blockchain.get_certificate(event_id)
    if not cert:
        raise HTTPException(status_code=400, detail="Cannot generate certificate: Event unverified or missing.")
    return cert


# =========================================================
# 9. RESTRICTED ZONES (POLYGON INTRUSION & ANOMALY RULES)
# =========================================================

@app.get("/api/zones")
def list_zones():
    return storage.get_zones()


@app.post("/api/zones")
def create_zone(zone: ZoneCreateRequest, current_user: dict = Depends(auth.get_current_user)):
    zone_id = f"zone-{len(storage.get_zones()) + 1}"
    z_dict = {
        "id": zone_id,
        "camera_id": zone.camera_id,
        "name": zone.name,
        "points": zone.points,
        "severity": zone.severity,
    }
    storage.add_zone(z_dict)
    return z_dict


@app.delete("/api/zones/{zone_id}")
def delete_zone_endpoint(zone_id: str, current_user: dict = Depends(auth.get_current_user)):
    storage.delete_zone(zone_id)
    return {"status": "deleted", "id": zone_id}


# =========================================================
# 10. BLOCKCHAIN LEDGER & FRAME HASH CHAIN
# =========================================================

@app.get("/api/ledger")
def get_ledger_entries():
    return ledger.get_ledger()


@app.get("/api/ledger/validate")
def validate_ledger_entries():
    return ledger.validate_ledger()


@app.get("/api/ledger/status")
def ledger_status():
    return ledger.get_ledger_status()


@app.get("/api/ledger/recent")
def ledger_recent(limit: int = 50):
    return ledger.get_recent_chain(limit=limit)


@app.get("/api/ledger/verify")
def ledger_verify(session_id: Optional[str] = None):
    return ledger.verify_frame_chain(session_id=session_id)


@app.get("/api/blockchain/chain")
def get_blockchain_chain():
    return storage.get_blockchain()


@app.get("/api/blockchain/validate")
def validate_blockchain_chain():
    valid, msg = blockchain.validate_chain()
    return {"valid": valid, "message": msg, "total_blocks": len(storage.get_blockchain())}
