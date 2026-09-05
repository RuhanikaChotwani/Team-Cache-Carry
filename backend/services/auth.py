"""Authentication and authorization service for IBVAP.
Provides secure PBKDF2-HMAC-SHA256 password hashing and standard JWT verification.
"""

import os
import json
import base64
import hmac
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status, Header, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = os.getenv("IBVAP_JWT_SECRET", "ibvap-secure-tactical-auth-key-2026-sih")
TOKEN_EXPIRE_HOURS = 24

security_scheme = HTTPBearer(auto_error=False)


# --- PBKDF2 Password Hashing ---

def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with a unique random salt."""
    salt = os.urandom(16).hex()
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    )
    return f"{salt}${iterations}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a password against the stored salt$iterations$derived string."""
    try:
        parts = stored_hash.split("$")
        if len(parts) != 3:
            return False
        salt, iterations_str, expected_hex = parts
        iterations = int(iterations_str)
        derived = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
        )
        return hmac.compare_digest(derived.hex(), expected_hex)
    except Exception:
        return False


# --- Standard Lightweight JWT (Zero external dependency) ---

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    padding = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode((s + padding).encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a standard signed HMAC-SHA256 JWT."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = data.copy()
    now = int(time.time())
    if expires_delta:
        exp = now + int(expires_delta.total_seconds())
    else:
        exp = now + (TOKEN_EXPIRE_HOURS * 3600)
    payload["iat"] = now
    payload["exp"] = exp

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and cryptographically verifies an access token."""
    try:
        parts = token.strip().split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts

        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        if payload.get("exp", 0) < int(time.time()):
            return None  # Expired

        return payload
    except Exception:
        return None


# --- FastAPI Dependencies ---

def get_token_from_request(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    token_query: Optional[str] = Query(None, alias="token"),
) -> Optional[str]:
    if auth_header and auth_header.credentials:
        return auth_header.credentials
    if token_query:
        return token_query
    return None


def get_current_user(token: Optional[str] = Depends(get_token_from_request)) -> dict:
    """Extracts and validates current authenticated user from request."""
    from services import storage

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in with Officer or Admin credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload["sub"]
    user = storage.get_user(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or revoked.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_optional_user(token: Optional[str] = Depends(get_token_from_request)) -> Optional[dict]:
    """Returns authenticated user if present and valid, otherwise None (no 401)."""
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    from services import storage
    return storage.get_user(payload["sub"])


def require_role(allowed_roles: list):
    """Dependency factory checking user has one of the allowed roles."""
    def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role", "officer")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {allowed_roles}",
            )
        return current_user
    return role_checker
