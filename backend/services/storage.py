"""SQLite storage layer for IBVAP.
Maintains persistent tables for cameras, events, alerts, blockchain ledger,
zones, calibrations, users, authorized personnel, authorized vehicles, and evidence records.
"""
import sqlite3, os, json, uuid
from datetime import datetime

DB_PATH = os.getenv("IBVAP_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "ibvap.db"))


def _db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = _db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS cameras (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT DEFAULT '',
        source TEXT DEFAULT 'mock',
        type TEXT DEFAULT 'mock',
        status TEXT DEFAULT 'IDLE',
        detection TEXT DEFAULT '',
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        time TEXT,
        camera_id TEXT,
        camera_name TEXT DEFAULT '',
        event_type TEXT,
        severity TEXT DEFAULT 'Low',
        status TEXT DEFAULT 'Active',
        description TEXT DEFAULT '',
        ai_metadata TEXT DEFAULT '{}'
    );
    CREATE TABLE IF NOT EXISTS alerts (
        id TEXT PRIMARY KEY,
        time TEXT,
        camera_id TEXT,
        camera_name TEXT DEFAULT '',
        event_type TEXT,
        severity TEXT DEFAULT 'Medium',
        description TEXT DEFAULT '',
        ai_metadata TEXT DEFAULT '{}',
        snapshot_path TEXT DEFAULT '',
        block_id INTEGER DEFAULT NULL,
        status TEXT DEFAULT 'Active'
    );
    CREATE TABLE IF NOT EXISTS blockchain (
        block_number INTEGER PRIMARY KEY,
        event_id TEXT,
        camera_id TEXT DEFAULT '',
        evidence_hash TEXT,
        metadata_hash TEXT,
        timestamp TEXT,
        previous_hash TEXT,
        block_hash TEXT,
        status TEXT DEFAULT 'Secured'
    );
    CREATE TABLE IF NOT EXISTS zones (
        id TEXT PRIMARY KEY,
        camera_id TEXT,
        name TEXT,
        points TEXT DEFAULT '[]',
        severity TEXT DEFAULT 'Critical'
    );
    CREATE TABLE IF NOT EXISTS calibrations (
        camera_id TEXT PRIMARY KEY,
        data TEXT DEFAULT '{}'
    );
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'officer',
        full_name TEXT DEFAULT '',
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS authorized_personnel (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        role_type TEXT DEFAULT 'Authorized',
        badge_id TEXT DEFAULT '',
        face_id TEXT DEFAULT '',
        department TEXT DEFAULT 'Border Security Force',
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS authorized_vehicles (
        id TEXT PRIMARY KEY,
        plate_number TEXT UNIQUE NOT NULL,
        vehicle_type TEXT DEFAULT 'Car',
        owner_name TEXT DEFAULT '',
        authorized_by TEXT DEFAULT 'Sector Command',
        status TEXT DEFAULT 'Active',
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS evidence_records (
        id TEXT PRIMARY KEY,
        event_id TEXT UNIQUE NOT NULL,
        track_id TEXT DEFAULT '',
        camera_id TEXT DEFAULT '',
        event_type TEXT DEFAULT '',
        classification TEXT DEFAULT '',
        zone_name TEXT DEFAULT '',
        severity TEXT DEFAULT 'High',
        confidence REAL DEFAULT 0.0,
        snapshot_path TEXT DEFAULT '',
        evidence_hash TEXT DEFAULT '',
        canonical_event_json TEXT DEFAULT '',
        event_hash TEXT DEFAULT '',
        blockchain_block INTEGER DEFAULT NULL,
        timestamp TEXT
    );
    """)
    conn.commit()

    # --- Seed Default Users if table empty ---
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        from services import auth
        admin_hash = auth.hash_password("admin123")
        officer_hash = auth.hash_password("officer123")
        now_str = datetime.utcnow().isoformat() + "Z"
        conn.execute(
            "INSERT INTO users (id, username, password_hash, role, full_name, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("usr-admin-01", "admin", admin_hash, "admin", "Commanding Officer / Admin", now_str),
        )
        conn.execute(
            "INSERT INTO users (id, username, password_hash, role, full_name, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("usr-officer-01", "officer", officer_hash, "officer", "Security Duty Officer", now_str),
        )
        conn.commit()

    # --- Seed Default Authorized Personnel if empty ---
    person_count = conn.execute("SELECT COUNT(*) FROM authorized_personnel").fetchone()[0]
    if person_count == 0:
        now_str = datetime.utcnow().isoformat() + "Z"
        default_personnel = [
            ("pers-01", "Major Devraj", "Army", "IND-ARMY-4421", "fcr-devraj", "Special Operations Command"),
            ("pers-02", "Captain Vikram", "Security", "BSF-SEC-1092", "fcr-vikram", "Border Patrol Sector 4"),
            ("pers-03", "Officer Sharma", "Authorized", "IB-AUTH-8831", "fcr-sharma", "Perimeter Surveillance"),
            ("pers-04", "Officer Rohan", "Authorized", "BSF-AUTH-7712", "fcr-rohan", "Checkpost Security"),
        ]
        for p in default_personnel:
            conn.execute(
                "INSERT INTO authorized_personnel (id, name, role_type, badge_id, face_id, department, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (p[0], p[1], p[2], p[3], p[4], p[5], now_str)
            )
        conn.commit()

    # --- Seed Default Authorized Vehicles if empty ---
    vehicle_count = conn.execute("SELECT COUNT(*) FROM authorized_vehicles").fetchone()[0]
    if vehicle_count == 0:
        now_str = datetime.utcnow().isoformat() + "Z"
        default_vehicles = [
            ("veh-01", "RJ14AB1234", "Patrol SUV", "Army Quick Reaction Team", "Border Post 1", "Active"),
            ("veh-02", "RJ14CD5678", "Supply Truck", "Quartermaster Corps", "HQ Logistics", "Active"),
            ("veh-03", "MH12AB1234", "Command Vehicle", "Sector Commander", "Sector Command", "Active"),
            ("veh-04", "DL04XY5678", "VIP Escort", "Security Escort Detail", "VIP Security", "Active"),
            ("veh-05", "SY14OAH", "Service Transport", "Tactical Maintenance Unit", "Station Depot", "Active"),
        ]
        for v in default_vehicles:
            conn.execute(
                "INSERT INTO authorized_vehicles (id, plate_number, vehicle_type, owner_name, authorized_by, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (v[0], v[1], v[2], v[3], v[4], v[5], now_str)
            )
        conn.commit()

    # --- Seed Default Restricted Zones if empty ---
    zone_count = conn.execute("SELECT COUNT(*) FROM zones").fetchone()[0]
    if zone_count == 0:
        # Default perimeter security zones (normalized 0.0 - 1.0 or pixel coordinates)
        zones_data = [
            {
                "id": "zone-restricted-01",
                "camera_id": "cam-01",
                "name": "Perimeter Red Zone",
                "points": json.dumps([[100, 150], [540, 150], [600, 450], [40, 450]]),
                "severity": "Critical",
            },
            {
                "id": "zone-gate-02",
                "camera_id": "cam-01",
                "name": "Security Gate Barrier",
                "points": json.dumps([[180, 240], [460, 240], [500, 400], [140, 400]]),
                "severity": "High",
            }
        ]
        for z in zones_data:
            conn.execute(
                "INSERT INTO zones (id, camera_id, name, points, severity) VALUES (?, ?, ?, ?, ?)",
                (z["id"], z["camera_id"], z["name"], z["points"], z["severity"])
            )
        conn.commit()

    conn.close()


# Automatically initialize DB on import
init_db()


# --- Camera CRUD ---
def get_cameras():
    conn = _db()
    rows = conn.execute("SELECT * FROM cameras ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_camera(camera_id):
    conn = _db()
    row = conn.execute("SELECT * FROM cameras WHERE id=?", (camera_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_camera(cam: dict):
    conn = _db()
    conn.execute(
        "INSERT INTO cameras (id,name,location,source,type,status,detection,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (cam["id"], cam["name"], cam["location"], cam["source"], cam["type"],
         cam.get("status", "IDLE"), cam.get("detection", ""), cam.get("created_at", datetime.utcnow().isoformat()))
    )
    conn.commit()
    conn.close()


def update_camera(camera_id, updates: dict):
    conn = _db()
    sets = ", ".join(f"{k}=?" for k in updates)
    vals = list(updates.values()) + [camera_id]
    conn.execute(f"UPDATE cameras SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


def delete_camera(camera_id):
    conn = _db()
    conn.execute("DELETE FROM cameras WHERE id=?", (camera_id,))
    conn.commit()
    conn.close()


# --- Events ---
def get_events(limit=100):
    conn = _db()
    rows = conn.execute("SELECT * FROM events ORDER BY time DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_event(event_id: str):
    conn = _db()
    row = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        try:
            d["ai_metadata"] = json.loads(d.get("ai_metadata", "{}"))
        except Exception:
            d["ai_metadata"] = {}
        return d
    return None


def add_event(evt: dict):
    conn = _db()
    conn.execute(
        "INSERT OR REPLACE INTO events (id,time,camera_id,camera_name,event_type,severity,status,description,ai_metadata) VALUES (?,?,?,?,?,?,?,?,?)",
        (evt["id"], evt["time"], evt["camera_id"], evt.get("camera_name", ""),
         evt["event_type"], evt.get("severity", "Low"), evt.get("status", "Active"),
         evt.get("description", ""), json.dumps(evt.get("ai_metadata", {})))
    )
    conn.commit()
    conn.close()


# --- Alerts ---
def get_alerts(limit=100):
    conn = _db()
    rows = conn.execute("SELECT * FROM alerts ORDER BY time DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["ai_metadata"] = json.loads(d.get("ai_metadata", "{}"))
        except Exception:
            d["ai_metadata"] = {}
        result.append(d)
    return result


def add_alert(alert: dict):
    conn = _db()
    conn.execute(
        "INSERT OR REPLACE INTO alerts (id,time,camera_id,camera_name,event_type,severity,description,ai_metadata,snapshot_path,block_id,status) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (alert["id"], alert["time"], alert.get("camera_id", "cam-01"), alert.get("camera_name", ""),
         alert["event_type"], alert.get("severity", "Medium"), alert.get("description", ""),
         json.dumps(alert.get("ai_metadata", {})), alert.get("snapshot_path", ""),
         alert.get("block_id"), alert.get("status", "Active"))
    )
    conn.commit()
    conn.close()


def update_alert(alert_id, updates: dict):
    conn = _db()
    sets = ", ".join(f"{k}=?" for k in updates)
    vals = list(updates.values()) + [alert_id]
    conn.execute(f"UPDATE alerts SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


def clear_alerts():
    conn = _db()
    conn.execute("DELETE FROM alerts")
    conn.commit()
    conn.close()


# --- Blockchain ---
def get_blockchain():
    conn = _db()
    rows = conn.execute("SELECT * FROM blockchain ORDER BY block_number ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_block(block: dict):
    conn = _db()
    conn.execute(
        "INSERT INTO blockchain (block_number,event_id,camera_id,evidence_hash,metadata_hash,timestamp,previous_hash,block_hash,status) VALUES (?,?,?,?,?,?,?,?,?)",
        (block["block_number"], block["event_id"], block.get("camera_id", ""),
         block["evidence_hash"], block["metadata_hash"], block["timestamp"],
         block["previous_hash"], block["block_hash"], block.get("status", "Secured"))
    )
    conn.commit()
    conn.close()


def get_last_block():
    conn = _db()
    row = conn.execute("SELECT * FROM blockchain ORDER BY block_number DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None


def get_block_by_event_id(event_id: str):
    conn = _db()
    row = conn.execute("SELECT * FROM blockchain WHERE event_id=?", (event_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Zones ---
def get_zones(camera_id=None):
    conn = _db()
    if camera_id:
        rows = conn.execute("SELECT * FROM zones WHERE camera_id=?", (camera_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM zones").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["points"] = json.loads(d["points"])
        except Exception:
            d["points"] = []
        result.append(d)
    return result


def add_zone(zone: dict):
    conn = _db()
    conn.execute(
        "INSERT OR REPLACE INTO zones (id,camera_id,name,points,severity) VALUES (?,?,?,?,?)",
        (zone["id"], zone["camera_id"], zone["name"],
         json.dumps(zone["points"]), zone.get("severity", "Critical"))
    )
    conn.commit()
    conn.close()


def delete_zone(zone_id: str):
    conn = _db()
    conn.execute("DELETE FROM zones WHERE id=?", (zone_id,))
    conn.commit()
    conn.close()


# --- Calibrations ---
def get_calibration(camera_id):
    conn = _db()
    row = conn.execute("SELECT * FROM calibrations WHERE camera_id=?", (camera_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        try:
            d["data"] = json.loads(d["data"])
        except Exception:
            d["data"] = {}
        return d["data"]
    return None


def set_calibration(camera_id, data: dict):
    conn = _db()
    conn.execute(
        "INSERT OR REPLACE INTO calibrations (camera_id, data) VALUES (?,?)",
        (camera_id, json.dumps(data))
    )
    conn.commit()
    conn.close()


# --- Users CRUD ---
def get_user(username: str) -> dict | None:
    conn = _db()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_user(username: str, password_hash: str, role: str = "officer", full_name: str = "") -> dict:
    conn = _db()
    uid = f"usr-{uuid.uuid4().hex[:6]}"
    now_str = datetime.utcnow().isoformat() + "Z"
    conn.execute(
        "INSERT INTO users (id, username, password_hash, role, full_name, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (uid, username, password_hash, role, full_name, now_str)
    )
    conn.commit()
    conn.close()
    return {"id": uid, "username": username, "role": role, "full_name": full_name, "created_at": now_str}


def list_users() -> list:
    conn = _db()
    rows = conn.execute("SELECT id, username, role, full_name, created_at FROM users").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Authorized Vehicles CRUD ---
def get_authorized_vehicles() -> list:
    conn = _db()
    rows = conn.execute("SELECT * FROM authorized_vehicles ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_plate_authorized(plate_text: str) -> tuple[bool, dict | None]:
    """Checks if a normalized plate string is in authorized_vehicles."""
    if not plate_text:
        return False, None
    clean = "".join(c for c in str(plate_text).upper() if c.isalnum())
    conn = _db()
    # Check exact match or without spaces
    row = conn.execute(
        "SELECT * FROM authorized_vehicles WHERE REPLACE(UPPER(plate_number), ' ', '') = ? AND status='Active'",
        (clean,)
    ).fetchone()
    conn.close()
    if row:
        return True, dict(row)
    return False, None


def add_authorized_vehicle(plate_number: str, vehicle_type: str = "Car", owner_name: str = "", authorized_by: str = "Command") -> dict:
    clean = "".join(c for c in str(plate_number).upper() if c.isalnum())
    conn = _db()
    vid = f"veh-{uuid.uuid4().hex[:6]}"
    now_str = datetime.utcnow().isoformat() + "Z"
    conn.execute(
        "INSERT OR REPLACE INTO authorized_vehicles (id, plate_number, vehicle_type, owner_name, authorized_by, status, created_at) VALUES (?, ?, ?, ?, ?, 'Active', ?)",
        (vid, clean, vehicle_type, owner_name, authorized_by, now_str)
    )
    conn.commit()
    conn.close()
    return {"id": vid, "plate_number": clean, "vehicle_type": vehicle_type, "owner_name": owner_name, "status": "Active"}


def delete_authorized_vehicle(plate_number: str) -> bool:
    clean = "".join(c for c in str(plate_number).upper() if c.isalnum())
    conn = _db()
    cur = conn.execute("DELETE FROM authorized_vehicles WHERE REPLACE(UPPER(plate_number), ' ', '') = ?", (clean,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# --- Authorized Personnel CRUD ---
def get_authorized_personnel() -> list:
    conn = _db()
    rows = conn.execute("SELECT * FROM authorized_personnel ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_person_authorized(name_or_face_id: str) -> tuple[bool, dict | None]:
    """Checks if an identified name or face_id belongs to authorized personnel."""
    if not name_or_face_id or name_or_face_id.lower() in ("unknown", "partial face", "person"):
        return False, None
    query = str(name_or_face_id).strip().lower()
    conn = _db()
    row = conn.execute(
        "SELECT * FROM authorized_personnel WHERE LOWER(name) = ? OR LOWER(name) LIKE ? OR face_id = ?",
        (query, f"%{query}%", query)
    ).fetchone()
    conn.close()
    if row:
        return True, dict(row)
    return False, None


def add_authorized_person(name: str, role_type: str = "Authorized", badge_id: str = "", face_id: str = "", department: str = "Border Security Force") -> dict:
    conn = _db()
    pid = f"pers-{uuid.uuid4().hex[:6]}"
    now_str = datetime.utcnow().isoformat() + "Z"
    conn.execute(
        "INSERT INTO authorized_personnel (id, name, role_type, badge_id, face_id, department, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (pid, name.strip(), role_type, badge_id, face_id, department, now_str)
    )
    conn.commit()
    conn.close()
    return {"id": pid, "name": name.strip(), "role_type": role_type, "badge_id": badge_id, "department": department}


def get_authorized_person_by_id(person_id: str) -> dict | None:
    conn = _db()
    row = conn.execute("SELECT * FROM authorized_personnel WHERE id = ? OR name = ?", (person_id, person_id)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def update_authorized_person(person_id: str, face_id: str = None, role_type: str = None, badge_id: str = None, department: str = None, name: str = None) -> bool:
    conn = _db()
    updates = []
    params = []
    if face_id is not None:
        updates.append("face_id = ?")
        params.append(face_id)
    if role_type is not None:
        updates.append("role_type = ?")
        params.append(role_type)
    if badge_id is not None:
        updates.append("badge_id = ?")
        params.append(badge_id)
    if department is not None:
        updates.append("department = ?")
        params.append(department)
    if name is not None:
        updates.append("name = ?")
        params.append(name.strip())

    if not updates:
        conn.close()
        return True

    params.extend([person_id, person_id])
    sql = f"UPDATE authorized_personnel SET {', '.join(updates)} WHERE id = ? OR name = ?"
    cur = conn.execute(sql, tuple(params))
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def delete_authorized_person(person_id: str) -> bool:
    conn = _db()
    cur = conn.execute("DELETE FROM authorized_personnel WHERE id = ? OR name = ?", (person_id, person_id))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# --- Evidence Records CRUD ---
def save_evidence_record(rec: dict) -> dict:
    conn = _db()
    eid = rec.get("id") or f"evrec-{uuid.uuid4().hex[:6]}"
    now_str = rec.get("timestamp") or (datetime.utcnow().isoformat() + "Z")
    conn.execute(
        """INSERT OR REPLACE INTO evidence_records 
           (id, event_id, track_id, camera_id, event_type, classification, zone_name, severity, confidence, snapshot_path, evidence_hash, canonical_event_json, event_hash, blockchain_block, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            eid,
            rec["event_id"],
            rec.get("track_id", ""),
            rec.get("camera_id", "cam-01"),
            rec.get("event_type", ""),
            rec.get("classification", ""),
            rec.get("zone_name", ""),
            rec.get("severity", "High"),
            rec.get("confidence", 0.0),
            rec.get("snapshot_path", ""),
            rec.get("evidence_hash", ""),
            rec.get("canonical_event_json", ""),
            rec.get("event_hash", ""),
            rec.get("blockchain_block"),
            now_str,
        )
    )
    conn.commit()
    conn.close()
    rec["id"] = eid
    rec["timestamp"] = now_str
    return rec


def get_evidence_record(event_id: str) -> dict | None:
    conn = _db()
    row = conn.execute("SELECT * FROM evidence_records WHERE event_id=?", (event_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_evidence_records(limit=100) -> list:
    conn = _db()
    rows = conn.execute("SELECT * FROM evidence_records ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_evidence_record(event_id: str, updates: dict):
    conn = _db()
    sets = ", ".join(f"{k}=?" for k in updates)
    vals = list(updates.values()) + [event_id]
    conn.execute(f"UPDATE evidence_records SET {sets} WHERE event_id=?", vals)
    conn.commit()
    conn.close()


# --- Counts for analytics ---
def count_table(table, where=None):
    conn = _db()
    q = f"SELECT COUNT(*) FROM {table}"
    params = ()
    if where:
        q += f" WHERE {where[0]}"
        params = where[1] if len(where) > 1 else ()
    row = conn.execute(q, params).fetchone()
    conn.close()
    return row[0] if row else 0
