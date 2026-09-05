"""Comprehensive Tamper Detection and Cryptographic Integrity Test Suite for IBVAP.
Tests:
PART A: Frame Hash Chain Tamper Detection
PART B: Blockchain Evidence Integrity (4 Core Scenarios):
  - TEST 1: Original event + original image -> VERIFIED
  - TEST 2: Modify image bytes -> EVIDENCE TAMPERED
  - TEST 3: Modify event metadata -> EVENT DATA TAMPERED
  - TEST 4: Modify both image and metadata -> BOTH TAMPERED
"""

import sys
import os
import copy
import json
import time
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from services import ledger, blockchain, storage


def test_frame_chain_tampering():
    print("------------------------------------------------------------")
    print("PART A: FRAME HASH CHAIN TAMPER DETECTION")
    print("------------------------------------------------------------")

    # 1. Start a test frame chain session
    print("[1] Starting test frame chain session...")
    ledger.start_frame_chain("tamper-test-session")

    # 2. Enqueue test frames
    print("[2] Enqueuing 10 test frame hashes...")
    for i in range(10):
        fake_jpeg = f"test-frame-{i}-{i*1234567}".encode("utf-8")
        ledger.enqueue_frame_hash(fake_jpeg, i + 1, "tamper-test-source")

    time.sleep(0.4)
    ledger.stop_frame_chain()

    # 3. Verify the chain is valid
    print("[3] Verifying untampered frame chain...")
    result = ledger.verify_frame_chain()
    print(f"    Valid: {result['valid']} | Message: {result['message']}")
    assert result["valid"], "Frame chain must be valid before tampering!"

    # 4. Tamper with record #3
    print("[4] Tampering with record #3 frame hash...")
    with ledger._chain_lock:
        original_chain = copy.deepcopy(ledger._frame_chain)

    if len(original_chain) >= 3:
        tampered_chain = copy.deepcopy(original_chain)
        tampered_chain[2]["frame_hash"] = "0" * 64
        with ledger._chain_lock:
            ledger._frame_chain = tampered_chain

        tamper_result = ledger.verify_frame_chain()
        print(f"    Tamper detected: {not tamper_result['valid']}")
        print(f"    Message: {tamper_result['message']}")
        assert not tamper_result["valid"], "Chain verification MUST fail when a frame hash is modified!"

        # Restore
        with ledger._chain_lock:
            ledger._frame_chain = original_chain
        restored_res = ledger.verify_frame_chain()
        assert restored_res["valid"], "Chain must be valid after restoration!"
        print("    -> Frame Chain Tamper Detection: PASSED [OK]")


def test_blockchain_evidence_tampering():
    print("\n------------------------------------------------------------")
    print("PART B: BLOCKCHAIN & FORENSIC EVIDENCE INTEGRITY SUITE")
    print("------------------------------------------------------------")

    event_id = f"EVT-TEST-{int(time.time())}"
    test_image_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"TACTICAL_EVIDENCE_SAMPLE_BYTES_ORIGINAL_442"
    
    event_data = {
        "event_id": event_id,
        "timestamp": "2026-09-05T19:42:31Z",
        "camera_id": "CAM-01",
        "track_id": "17",
        "event_type": "UNAUTHORIZED_PERSON_INTRUSION",
        "classification": "Unknown Person",
        "zone_name": "Perimeter Red Zone",
        "confidence": 0.91,
        "severity": "High",
    }

    print(f"\nSetting up security incident '{event_id}'...")
    rec_res = blockchain.record_security_event_blockchain(
        event_id=event_id,
        event_data=event_data,
        evidence_bytes=test_image_bytes,
        camera_id="CAM-01",
    )
    print(f"  Secured in Block #{rec_res['block']['block_number']}")
    print(f"  Evidence SHA-256: {rec_res['evidence_record']['evidence_hash']}")
    print(f"  Event SHA-256:    {rec_res['evidence_record']['event_hash']}")

    evidence_file_path = blockchain.EVIDENCE_DIR / f"{event_id}.jpg"
    assert evidence_file_path.exists(), "Evidence file must be written to disk"

    # -------------------------------------------------------------
    # TEST 1: Original event + original image -> VERIFIED
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing Original Event + Original Image Bytes...")
    res1 = blockchain.verify_event_integrity(event_id)
    print(f"  Status:             {res1['status']}")
    print(f"  Verified:           {res1['verified']}")
    print(f"  Event Integrity:    {res1['event_integrity']}")
    print(f"  Evidence Integrity: {res1['evidence_integrity']}")
    print(f"  Blockchain Link:    {res1['blockchain_record']}")
    assert res1["verified"] is True, "TEST 1 FAILED: Original event must be VERIFIED!"
    assert res1["status"] == "VERIFIED", f"Expected VERIFIED, got {res1['status']}"
    assert res1["event_integrity"] == "MATCH"
    assert res1["evidence_integrity"] == "MATCH"
    print("  -> TEST 1 PASSED: Original data is 100% VERIFIED.")

    # -------------------------------------------------------------
    # TEST 2: Modify image bytes -> EVIDENCE TAMPERED
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing Image Tampering (Modifying evidence bytes on disk)...")
    tampered_bytes = test_image_bytes + b"_TAMPERED_MODIFIED_BYTE_INSERTION"
    with open(evidence_file_path, "wb") as f:
        f.write(tampered_bytes)

    res2 = blockchain.verify_event_integrity(event_id)
    print(f"  Status:             {res2['status']}")
    print(f"  Verified:           {res2['verified']}")
    print(f"  Event Integrity:    {res2['event_integrity']}")
    print(f"  Evidence Integrity: {res2['evidence_integrity']}")
    print(f"  Message:            {res2['message']}")
    assert res2["verified"] is False, "TEST 2 FAILED: Tampered image must NOT be verified!"
    assert res2["status"] == "EVIDENCE_TAMPERED", f"Expected EVIDENCE_TAMPERED, got {res2['status']}"
    assert res2["evidence_integrity"] == "MISMATCH"
    assert res2["event_integrity"] == "MATCH"
    print("  -> TEST 2 PASSED: Evidence tampering correctly detected and isolated.")

    # Restore original image bytes for Test 3
    with open(evidence_file_path, "wb") as f:
        f.write(test_image_bytes)

    # -------------------------------------------------------------
    # TEST 3: Modify event metadata -> EVENT DATA TAMPERED
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing Event Metadata Tampering (Altering confidence in SQLite)...")
    original_rec = storage.get_evidence_record(event_id)
    storage.update_evidence_record(event_id, {"confidence": 0.45})

    res3 = blockchain.verify_event_integrity(event_id)
    print(f"  Status:             {res3['status']}")
    print(f"  Verified:           {res3['verified']}")
    print(f"  Event Integrity:    {res3['event_integrity']}")
    print(f"  Evidence Integrity: {res3['evidence_integrity']}")
    print(f"  Message:            {res3['message']}")
    assert res3["verified"] is False, "TEST 3 FAILED: Tampered metadata must NOT be verified!"
    assert res3["status"] == "EVENT_DATA_TAMPERED", f"Expected EVENT_DATA_TAMPERED, got {res3['status']}"
    assert res3["event_integrity"] == "MISMATCH"
    assert res3["evidence_integrity"] == "MATCH"
    print("  -> TEST 3 PASSED: Event metadata tampering correctly detected and isolated.")

    # -------------------------------------------------------------
    # TEST 4: Modify both image and metadata -> BOTH TAMPERED
    # -------------------------------------------------------------
    print("\n[TEST 4] Testing Dual Tampering (Both image bytes and metadata modified)...")
    with open(evidence_file_path, "wb") as f:
        f.write(tampered_bytes)
    # metadata is already modified from Test 3

    res4 = blockchain.verify_event_integrity(event_id)
    print(f"  Status:             {res4['status']}")
    print(f"  Verified:           {res4['verified']}")
    print(f"  Event Integrity:    {res4['event_integrity']}")
    print(f"  Evidence Integrity: {res4['evidence_integrity']}")
    print(f"  Message:            {res4['message']}")
    assert res4["verified"] is False, "TEST 4 FAILED: Dual tampered data must NOT be verified!"
    assert res4["status"] == "BOTH_TAMPERED", f"Expected BOTH_TAMPERED, got {res4['status']}"
    assert res4["evidence_integrity"] == "MISMATCH"
    assert res4["event_integrity"] == "MISMATCH"
    print("  -> TEST 4 PASSED: Dual tampering correctly detected.")

    # Cleanup: restore original file and record
    with open(evidence_file_path, "wb") as f:
        f.write(test_image_bytes)
    storage.update_evidence_record(event_id, {"confidence": original_rec["confidence"]})

    # Final check that restored state is VERIFIED again
    clean_res = blockchain.verify_event_integrity(event_id)
    assert clean_res["verified"] is True, "Must return to VERIFIED when restored"
    print(f"\nCleanup check: Restored state is {clean_res['status']}.")


def run_all_tamper_tests():
    print("============================================================")
    print("IBVAP TAMPER DETECTION AND BLOCKCHAIN INTEGRITY TEST SUITE")
    print("============================================================")
    test_frame_chain_tampering()
    test_blockchain_evidence_tampering()
    print("\n============================================================")
    print("ALL 4 BLOCKCHAIN TAMPER TESTS + FRAME CHAIN TESTS PASSED [100%]")
    print("============================================================")


if __name__ == "__main__":
    run_all_tamper_tests()
