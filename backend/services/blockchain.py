"""Blockchain evidence integrity service for IBVAP.
Provides deterministic canonical event hashing, raw evidence byte hashing,
blockchain ledger anchoring, and forensic backend verification.
"""

import hashlib
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

from services import storage

GENESIS_PREV = "0" * 64
EVIDENCE_DIR = Path(__file__).resolve().parent.parent / "data" / "evidence"


def canonicalize_event(event_dict: dict) -> bytes:
    """Produces a deterministic, canonical UTF-8 byte string for an event.
    Enforces sorted keys, compact separators, and consistent value formatting.
    """
    canonical_keys = [
        "camera_id",
        "classification",
        "confidence",
        "event_id",
        "event_type",
        "evidence_file",
        "timestamp",
        "track_id",
        "zone",
    ]
    clean = {}
    for k in canonical_keys:
        if k in event_dict:
            val = event_dict[k]
            if isinstance(val, float):
                clean[k] = round(val, 2)
            elif isinstance(val, (int, str)):
                clean[k] = str(val)
            else:
                clean[k] = str(val) if val is not None else ""
        else:
            clean[k] = ""
    return json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def calculate_evidence_hash(evidence_bytes: bytes) -> str:
    """SHA-256 fingerprint computed directly from the ACTUAL BYTES of the evidence image."""
    return hashlib.sha256(evidence_bytes).hexdigest()


def calculate_event_hash(canonical_bytes: bytes) -> str:
    """SHA-256 fingerprint of the canonicalized event JSON."""
    return hashlib.sha256(canonical_bytes).hexdigest()


def calculate_block_hash(
    block_number: int,
    event_id: str,
    evidence_hash: str,
    timestamp: str,
    previous_hash: str,
    metadata_hash: str = "",
) -> str:
    """Cryptographic hash linking this block to the previous block in the chain."""
    block_data = {
        "block_number": block_number,
        "event_id": event_id,
        "evidence_hash": evidence_hash,
        "metadata_hash": metadata_hash,
        "previous_hash": previous_hash,
        "timestamp": timestamp,
    }
    encoded = json.dumps(block_data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def record_security_event_blockchain(
    event_id: str,
    event_data: dict,
    evidence_bytes: bytes,
    camera_id: str = "CAM-01",
) -> dict:
    """Secures a security event and its first-entry evidence onto the tamper-proof blockchain.
    1. Saves evidence image to disk.
    2. Calculates SHA-256 of raw image bytes.
    3. Reconstructs canonical event JSON and computes event SHA-256.
    4. Anchors both hashes into the append-only blockchain block.
    5. Saves full evidence record in SQLite.
    """
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    evidence_filename = f"{event_id}.jpg"
    evidence_file_path = EVIDENCE_DIR / evidence_filename

    # Save raw bytes
    with open(evidence_file_path, "wb") as f:
        f.write(evidence_bytes)

    # 1. Compute Evidence Hash on actual bytes
    evidence_hash = calculate_evidence_hash(evidence_bytes)

    # 2. Canonicalize event dictionary and compute Event Hash
    canonical_event = {
        "event_id": event_id,
        "timestamp": event_data.get("timestamp") or (datetime.utcnow().isoformat() + "Z"),
        "camera_id": camera_id,
        "track_id": event_data.get("track_id", "0"),
        "event_type": event_data.get("event_type", "SECURITY_ALERT"),
        "classification": event_data.get("classification", "Unknown Person"),
        "zone": event_data.get("zone_name") or event_data.get("zone", "Restricted Area"),
        "confidence": float(event_data.get("confidence", 0.90)),
        "evidence_file": evidence_filename,
    }
    canonical_bytes = canonicalize_event(canonical_event)
    event_hash = calculate_event_hash(canonical_bytes)

    # 3. Create blockchain block
    last = storage.get_last_block()
    block_number = (last["block_number"] + 1) if last else 1
    previous_hash = last["block_hash"] if last else GENESIS_PREV
    timestamp = canonical_event["timestamp"]

    block_hash = calculate_block_hash(
        block_number, event_id, evidence_hash, timestamp, previous_hash, metadata_hash=event_hash
    )

    block = {
        "block_number": block_number,
        "event_id": event_id,
        "camera_id": camera_id,
        "evidence_hash": evidence_hash,
        "metadata_hash": event_hash,
        "timestamp": timestamp,
        "previous_hash": previous_hash,
        "block_hash": block_hash,
        "status": "Secured",
    }
    storage.add_block(block)

    # 4. Save into SQLite evidence_records
    evidence_record = {
        "event_id": event_id,
        "track_id": canonical_event["track_id"],
        "camera_id": camera_id,
        "event_type": canonical_event["event_type"],
        "classification": canonical_event["classification"],
        "zone_name": canonical_event["zone"],
        "severity": event_data.get("severity", "High"),
        "confidence": canonical_event["confidence"],
        "snapshot_path": f"/api/evidence/{evidence_filename}",
        "evidence_hash": evidence_hash,
        "canonical_event_json": canonical_bytes.decode("utf-8"),
        "event_hash": event_hash,
        "blockchain_block": block_number,
        "timestamp": timestamp,
    }
    storage.save_evidence_record(evidence_record)

    return {
        "block": block,
        "evidence_record": evidence_record,
        "canonical_json": canonical_bytes.decode("utf-8"),
    }


def verify_event_integrity(event_id: str) -> dict:
    """Forensically verifies an event and its evidence against the blockchain ledger.
    Steps:
    1. Load recorded event metadata from storage.
    2. Load evidence image file from disk.
    3. Calculate current evidence SHA-256.
    4. Reconstruct canonical event JSON.
    5. Calculate current event SHA-256.
    6. Retrieve recorded block from blockchain table.
    7. Compare evidence hash, event hash, and block hash.
    8. Return MATCH or TAMPERED.
    """
    rec = storage.get_evidence_record(event_id)
    if not rec:
        return {
            "verified": False,
            "status": "EVENT_NOT_FOUND",
            "message": f"No evidence record found for event ID '{event_id}'.",
            "event_id": event_id,
        }

    block = storage.get_block_by_event_id(event_id)
    if not block:
        return {
            "verified": False,
            "status": "NO_BLOCKCHAIN_RECORD",
            "message": f"Event '{event_id}' has no corresponding blockchain block.",
            "event_id": event_id,
        }

    # 1. Check evidence image file on disk
    evidence_filename = f"{event_id}.jpg"
    evidence_file_path = EVIDENCE_DIR / evidence_filename

    if not evidence_file_path.exists():
        return {
            "verified": False,
            "status": "EVIDENCE_FILE_MISSING",
            "message": f"Evidence image file '{evidence_filename}' is missing from disk storage.",
            "event_id": event_id,
            "blockchain_evidence_hash": block["evidence_hash"],
        }

    with open(evidence_file_path, "rb") as f:
        current_evidence_bytes = f.read()

    current_evidence_hash = calculate_evidence_hash(current_evidence_bytes)
    evidence_match = (current_evidence_hash == block["evidence_hash"])

    # 2. Reconstruct canonical event JSON from current record
    current_canonical_dict = {
        "event_id": rec["event_id"],
        "timestamp": rec["timestamp"],
        "camera_id": rec.get("camera_id", "cam-01"),
        "track_id": rec.get("track_id", "0"),
        "event_type": rec.get("event_type", ""),
        "classification": rec.get("classification", ""),
        "zone": rec.get("zone_name", ""),
        "confidence": float(rec.get("confidence", 0.0)),
        "evidence_file": evidence_filename,
    }
    current_canonical_bytes = canonicalize_event(current_canonical_dict)
    current_event_hash = calculate_event_hash(current_canonical_bytes)
    event_match = (current_event_hash == block["metadata_hash"])

    # 3. Verify block hash calculation
    recalc_block_hash = calculate_block_hash(
        block["block_number"],
        block["event_id"],
        block["evidence_hash"],
        block["timestamp"],
        block["previous_hash"],
        metadata_hash=block["metadata_hash"],
    )
    blockchain_block_intact = (recalc_block_hash == block["block_hash"])

    # 4. Synthesize overall verdict
    if evidence_match and event_match and blockchain_block_intact:
        status_code = "VERIFIED"
        message = "Integrity verified: Event metadata and first-entry evidence match the immutable blockchain record exactly."
        verified = True
    elif not evidence_match and event_match:
        status_code = "EVIDENCE_TAMPERED"
        message = "TAMPERING DETECTED: The stored evidence image file has been modified or replaced! SHA-256 mismatch."
        verified = False
    elif evidence_match and not event_match:
        status_code = "EVENT_DATA_TAMPERED"
        message = "TAMPERING DETECTED: Event metadata attributes have been altered after recording! Canonical SHA-256 mismatch."
        verified = False
    else:
        status_code = "BOTH_TAMPERED"
        message = "CRITICAL TAMPERING DETECTED: Both evidence image and event metadata have been compromised!"
        verified = False

    return {
        "verified": verified,
        "status": status_code,
        "message": message,
        "event_id": event_id,
        "block_number": block["block_number"],
        "event_integrity": "MATCH" if event_match else "MISMATCH",
        "evidence_integrity": "MATCH" if evidence_match else "MISMATCH",
        "blockchain_record": "MATCH" if blockchain_block_intact else "CORRUPTED",
        "current_evidence_hash": current_evidence_hash,
        "blockchain_evidence_hash": block["evidence_hash"],
        "current_event_hash": current_event_hash,
        "blockchain_event_hash": block["metadata_hash"],
        "timestamp": block["timestamp"],
    }


def validate_chain() -> tuple[bool, str]:
    """Validates the cryptographic chain of all blocks in SQLite."""
    chain = storage.get_blockchain()
    if not chain:
        return True, "Blockchain ledger is initialized and empty."

    for i, block in enumerate(chain):
        recalc = calculate_block_hash(
            block["block_number"],
            block["event_id"],
            block["evidence_hash"],
            block["timestamp"],
            block["previous_hash"],
            block.get("metadata_hash", ""),
        )
        if recalc != block["block_hash"]:
            return False, f"Block #{block['block_number']} block_hash is invalid (tampered)."

        if i == 0:
            if block["previous_hash"] != GENESIS_PREV:
                return False, "Genesis block has invalid previous hash link."
        else:
            if block["previous_hash"] != chain[i - 1]["block_hash"]:
                return False, f"Block #{block['block_number']} is not linked to previous block #{chain[i-1]['block_number']}."

    return True, f"All {len(chain)} blocks are cryptographically intact and unbroken."


def get_certificate(event_id: str) -> Optional[dict]:
    """Generates an official verification certificate for an event."""
    v_result = verify_event_integrity(event_id)
    if not v_result.get("verified"):
        return None

    chain_valid, chain_msg = validate_chain()
    return {
        "certificate_id": f"CERT-{event_id.replace('EVT-', '')}-{datetime.utcnow().strftime('%Y%m%d')}",
        "event_id": event_id,
        "verified": True,
        "evidence_hash": v_result["current_evidence_hash"],
        "event_hash": v_result["current_event_hash"],
        "block_number": v_result["block_number"],
        "chain_valid": chain_valid,
        "issued_at": datetime.utcnow().isoformat() + "Z",
        "authority": "IBVAP Autonomous Border Surveillance & Forensic Verification Node",
    }
