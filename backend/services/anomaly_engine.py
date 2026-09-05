"""Anomaly Rule Engine for IBVAP.
Evaluates spatial zones (polygon intrusion, line crossing, loitering) and
semantic classifications (Authorized vs Unknown Person, Registered vs Unregistered Vehicle, Animal Threats).
"""

import time
import json
import logging
from typing import List, Dict, Tuple, Optional, Any
from services import storage

logger = logging.getLogger("ibvap.anomaly")

# Cooldown per track to prevent alert flooding (seconds)
ALERT_COOLDOWN = 15.0
_last_track_alerts: Dict[str, float] = {}
_track_zone_entry_time: Dict[str, Dict[str, float]] = {}  # track_id -> {zone_id: first_entry_timestamp}

# Supported COCO Animal Classes for Border Surveillance
COCO_ANIMAL_CLASSES = (
    "animal", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe"
)


def is_point_in_polygon(x: float, y: float, polygon: list) -> bool:
    """Ray casting algorithm for testing point in polygon.
    Polygon is a list of [x, y] coordinates.
    """
    if not polygon or len(polygon) < 3:
        return False

    n = len(polygon)
    inside = False
    p1x, p1y = polygon[0]

    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def check_point_in_zones(x: float, y: float, zones: list) -> List[dict]:
    """Finds all zones containing the coordinate (x, y)."""
    matched_zones = []
    for z in zones:
        pts = z.get("points") or []
        if isinstance(pts, str):
            try:
                pts = json.loads(pts)
            except Exception:
                pts = []
        if is_point_in_polygon(x, y, pts):
            matched_zones.append(z)
    return matched_zones


def evaluate_anomalies(
    camera_id: str,
    tracked_entities: List[dict],
    zones: Optional[List[dict]] = None,
) -> List[dict]:
    """Evaluates surveillance rules against current tracked entities.
    
    tracked_entities items:
    {
        "track_id": "17",
        "class": "person" | "car" | "animal" | etc.,
        "classification": "Authorized Person" | "Unknown Person" | "Authorized Vehicle" | "Unregistered Vehicle" | "Animal" | "Potential Animal Threat",
        "confidence": 0.91,
        "bbox": [x1, y1, x2, y2],
        "identity": "Major Devraj" | "Unknown",
        "plate_text": "RJ14AB1234" | None,
        "first_entry_bytes": b"..." | None,
        "first_entry_time": "...",
    }

    Returns list of generated alert dictionaries.
    """
    global _last_track_alerts, _track_zone_entry_time

    if zones is None:
        zones = storage.get_zones(camera_id) or storage.get_zones()

    now = time.time()
    generated_alerts = []

    for entity in tracked_entities:
        track_id = str(entity.get("track_id", "0"))
        bbox = entity.get("bbox", [0, 0, 0, 0])
        cls = entity.get("class", "person").lower()
        classification = entity.get("classification", "Unknown Person")
        confidence = float(entity.get("confidence", 0.8))
        identity = entity.get("identity", "Unknown")
        plate_text = entity.get("plate_text")

        # =============================================================
        # Rule 0: WATCHLIST MATCH — Highest Security Priority
        # Fires for ANY entity classified as "Watchlist Match",
        # regardless of zone. A watchlist match IS a security event.
        # =============================================================
        if classification == "Watchlist Match" and identity != "Unknown":
            alert_key = f"{track_id}_watchlist_match"
            if now - _last_track_alerts.get(alert_key, 0.0) >= ALERT_COOLDOWN:
                _last_track_alerts[alert_key] = now
                generated_alerts.append({
                    "event_type": "WATCHLIST_MATCH",
                    "classification": "Watchlist Match",
                    "severity": "HIGH",
                    "camera_id": camera_id,
                    "zone_name": "All Zones",
                    "track_id": track_id,
                    "confidence": confidence,
                    "description": f"Watchlist match detected: {identity} (Track #{track_id}, Confidence: {round(confidence * 100)}%)",
                    "metadata": {
                        "track_id": track_id,
                        "identity": identity,
                        "bbox": bbox,
                        "match_type": "watchlist",
                    }
                })
            # Watchlist matches still go through zone checks below
            # (they may also trigger zone intrusion alerts)

        # Use bottom center point (feet/ground contact point) for spatial ground plane check
        bx = (bbox[0] + bbox[2]) / 2.0
        by = float(bbox[3])

        matched_zones = check_point_in_zones(bx, by, zones)
        if not matched_zones:
            # Clean up entry times if entity left zone
            if track_id in _track_zone_entry_time:
                _track_zone_entry_time.pop(track_id, None)
            continue

        for zone in matched_zones:
            zone_id = zone.get("id", "zone-0")
            zone_name = zone.get("name", "Restricted Area")
            zone_severity = zone.get("severity", "High")

            # Track dwell time
            if track_id not in _track_zone_entry_time:
                _track_zone_entry_time[track_id] = {}
            if zone_id not in _track_zone_entry_time[track_id]:
                _track_zone_entry_time[track_id][zone_id] = now

            dwell_seconds = now - _track_zone_entry_time[track_id][zone_id]

            # Rule 1: Unknown Person in Restricted Zone
            # Authorized personnel are EXEMPT from intrusion alerts
            # Animals are strictly excluded from person alerts
            if (
                (classification == "Unknown Person" or (cls == "person" and not storage.is_person_authorized(identity)[0]))
                and cls not in COCO_ANIMAL_CLASSES
                and classification not in ("Animal", "Potential Animal Threat")
            ):
                alert_key = f"{track_id}_unknown_person_{zone_id}"
                if now - _last_track_alerts.get(alert_key, 0.0) >= ALERT_COOLDOWN:
                    _last_track_alerts[alert_key] = now
                    generated_alerts.append({
                        "event_type": "UNAUTHORIZED_PERSON_INTRUSION",
                        "classification": "Unknown Person",
                        "severity": "High" if zone_severity != "Critical" else "Critical",
                        "camera_id": camera_id,
                        "zone_name": zone_name,
                        "track_id": track_id,
                        "confidence": confidence,
                        "description": f"Unknown Person detected entering restricted zone '{zone_name}' (Track #{track_id})",
                        "metadata": {
                            "track_id": track_id,
                            "identity": "Unknown",
                            "zone": zone_name,
                            "zone_id": zone_id,
                            "bbox": bbox,
                            "dwell_seconds": round(dwell_seconds, 1),
                        }
                    })

            # Rule 2: Unregistered Vehicle in Restricted Zone
            # Authorized vehicles are EXEMPT from unregistered vehicle alerts
            elif classification == "Unregistered Vehicle" or (cls in ("car", "truck", "motorcycle") and plate_text and not storage.is_plate_authorized(plate_text)[0]):
                alert_key = f"{track_id}_unregistered_vehicle_{zone_id}"
                if now - _last_track_alerts.get(alert_key, 0.0) >= ALERT_COOLDOWN:
                    _last_track_alerts[alert_key] = now
                    generated_alerts.append({
                        "event_type": "UNREGISTERED_VEHICLE_INTRUSION",
                        "classification": "Unregistered Vehicle",
                        "severity": "High",
                        "camera_id": camera_id,
                        "zone_name": zone_name,
                        "track_id": track_id,
                        "confidence": confidence,
                        "description": f"Unregistered Vehicle ({plate_text or 'Plate Unreadable'}) entered security perimeter '{zone_name}' (Track #{track_id})",
                        "metadata": {
                            "track_id": track_id,
                            "plate_text": plate_text or "UNREGISTERED",
                            "zone": zone_name,
                            "zone_id": zone_id,
                            "bbox": bbox,
                            "dwell_seconds": round(dwell_seconds, 1),
                        }
                    })

            # Rule 3: Animal Threat in Restricted Zone
            # Animal detected + inside restricted zone -> Potential Animal Threat
            # Exclude humans strictly to avoid false human-as-animal misclassification
            elif (
                classification in ("Animal", "Potential Animal Threat")
                or cls in COCO_ANIMAL_CLASSES
            ) and cls != "person" and classification not in ("Watchlist Match", "Authorized Person", "Unknown Person"):
                # Elevate classification to Potential Animal Threat when inside restricted zone
                entity["classification"] = "Potential Animal Threat"
                alert_key = f"{track_id}_animal_threat_{zone_id}"
                if now - _last_track_alerts.get(alert_key, 0.0) >= ALERT_COOLDOWN:
                    _last_track_alerts[alert_key] = now
                    animal_name = cls.upper() if cls != "animal" else (str(identity).upper() if identity != "Unknown" else "ANIMAL")
                    generated_alerts.append({
                        "event_type": "POTENTIAL_ANIMAL_THREAT",
                        "classification": "Potential Animal Threat",
                        "severity": "Medium" if zone_severity != "Critical" else "High",
                        "camera_id": camera_id,
                        "zone_name": zone_name,
                        "track_id": track_id,
                        "confidence": confidence,
                        "description": f"Potential Animal Threat ({animal_name}) breached boundary '{zone_name}' (Track #{track_id})",
                        "metadata": {
                            "track_id": track_id,
                            "animal_type": cls,
                            "identity": identity,
                            "zone": zone_name,
                            "zone_id": zone_id,
                            "bbox": bbox,
                            "dwell_seconds": round(dwell_seconds, 1),
                        }
                    })

            # Rule 4: Loitering (Track remaining in zone > 12 seconds)
            if dwell_seconds > 12.0 and classification not in ("Authorized Person", "Authorized Vehicle"):
                alert_key = f"{track_id}_loitering_{zone_id}"
                if now - _last_track_alerts.get(alert_key, 0.0) >= (ALERT_COOLDOWN * 2):
                    _last_track_alerts[alert_key] = now
                    generated_alerts.append({
                        "event_type": "ZONE_LOITERING",
                        "classification": classification,
                        "severity": "Medium",
                        "camera_id": camera_id,
                        "zone_name": zone_name,
                        "track_id": track_id,
                        "confidence": confidence,
                        "description": f"Extended dwell/loitering ({round(dwell_seconds)}s) detected in '{zone_name}' (Track #{track_id})",
                        "metadata": {
                            "track_id": track_id,
                            "zone": zone_name,
                            "dwell_seconds": round(dwell_seconds, 1),
                            "bbox": bbox,
                        }
                    })

    return generated_alerts
