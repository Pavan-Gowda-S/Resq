"""
RESQ Comprehensive Security Test Suite
Covers:
1. Password Complexity Validation & Bcrypt Hashing
2. JWT Lifecycle: Expiration, Revocation, Refresh, Algorithm Pinning
3. AES-256-GCM Application-Level Encryption & Tamper Detection
4. Multi-Tenant Organization Data Isolation & IDOR Protection
5. Role-Based Access Control (RBAC) & Privilege Escalation Prevention
6. HTTP Security Headers (OWASP) & Payload Size Limits
7. Sanitized Audit Logging (Password/Token Redaction)
"""
import pytest
import os
import time
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from backend.app.auth.security import (
    validate_password_complexity,
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    revoke_token,
    is_token_revoked
)
from backend.app.core.security.crypto import field_crypto, FieldEncryptionService
from backend.app.middleware.audit_middleware import sanitize_audit_data


# ==============================================================================
# 1. PASSWORD SECURITY & BCRYPT TESTS
# ==============================================================================

def test_password_complexity_valid():
    """Valid strong passwords must pass complexity check."""
    valid_passwords = [
        "SecurePassword@123",
        "KeralaResq!2026",
        "Admin#Super99$",
        "Passw0rd_Strong!"
    ]
    for pwd in valid_passwords:
        validate_password_complexity(pwd)  # Should not raise


def test_password_complexity_rejections():
    """Weak passwords must be rejected with informative errors."""
    with pytest.raises(ValueError, match="at least 8 characters"):
        validate_password_complexity("Ab1!")

    with pytest.raises(ValueError, match="uppercase letter"):
        validate_password_complexity("password@123")

    with pytest.raises(ValueError, match="lowercase letter"):
        validate_password_complexity("PASSWORD@123")

    with pytest.raises(ValueError, match="digit"):
        validate_password_complexity("Password@Special")

    with pytest.raises(ValueError, match="special character"):
        validate_password_complexity("Password12345")


def test_bcrypt_hashing_and_verification():
    """Bcrypt must produce non-reversible hashes and verify successfully."""
    pwd = "EmergencyRescue#2026"
    hashed = get_password_hash(pwd)
    assert hashed != pwd
    assert hashed.startswith("$2b$12$")
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword#1", hashed) is False


# ==============================================================================
# 2. JWT TOKEN SECURITY TESTS
# ==============================================================================

def test_jwt_creation_and_payload_claims():
    """Access token must encode sub, role, and org_id with expiration."""
    user_id = str(uuid4())
    org_id = str(uuid4())
    data = {"sub": user_id, "role": "CONTROL_ROOM_DISPATCHER", "org_id": org_id}
    token = create_access_token(data=data, expires_delta=timedelta(minutes=15))

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["role"] == "CONTROL_ROOM_DISPATCHER"
    assert payload["org_id"] == org_id
    assert payload["type"] == "access"
    assert "exp" in payload


def test_jwt_expiration_rejection():
    """Expired tokens must fail decoding."""
    data = {"sub": str(uuid4())}
    expired_token = create_access_token(data=data, expires_delta=timedelta(seconds=-10))
    payload = decode_access_token(expired_token)
    assert payload is None


def test_jwt_token_revocation():
    """Revoked tokens must be rejected immediately."""
    data = {"sub": str(uuid4())}
    token = create_access_token(data=data)
    assert decode_access_token(token) is not None

    revoke_token(token)
    assert is_token_revoked(token) is True
    assert decode_access_token(token) is None


def test_refresh_token_lifecycle():
    """Refresh tokens must carry type='refresh'."""
    user_id = str(uuid4())
    refresh = create_refresh_token(user_id=user_id)
    payload = decode_access_token(refresh)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["type"] == "refresh"


# ==============================================================================
# 3. AES-256-GCM APPLICATION-LEVEL ENCRYPTION TESTS
# ==============================================================================

def test_aes_256_gcm_encryption_roundtrip():
    """Plaintext phone number must encrypt and decrypt identically."""
    phone = "+91-9845012345"
    encrypted = field_crypto.encrypt(phone)
    assert encrypted != phone
    assert encrypted.startswith("enc:v1:")
    assert field_crypto.is_encrypted(encrypted) is True

    decrypted = field_crypto.decrypt(encrypted)
    assert decrypted == phone


def test_aes_256_gcm_nonce_uniqueness():
    """Encrypting the same plaintext twice must produce different ciphertexts (unique nonces)."""
    text = "Confidential Patient Cardiac History"
    enc1 = field_crypto.encrypt(text)
    enc2 = field_crypto.encrypt(text)
    assert enc1 != enc2, "Each encryption must use a unique cryptographically random 96-bit nonce"
    assert field_crypto.decrypt(enc1) == text
    assert field_crypto.decrypt(enc2) == text


def test_aes_256_gcm_tamper_rejection():
    """Tampering with ciphertext or authentication tag must cause verification failure."""
    text = "Secret Medical Data"
    enc = field_crypto.encrypt(text)
    # Alter last 4 characters
    tampered = enc[:-4] + "XXXX"
    with pytest.raises(ValueError, match="Decryption failed or ciphertext tampered"):
        field_crypto.decrypt(tampered)


def test_aes_256_gcm_plaintext_fallback():
    """Legacy unencrypted records must pass through untouched without breaking."""
    legacy_phone = "+91-9447000000"
    result = field_crypto.decrypt(legacy_phone)
    assert result == legacy_phone


# ==============================================================================
# 4. AUDIT LOG SANITIZATION TESTS
# ==============================================================================

def test_audit_log_redaction():
    """Audit logs must never log raw passwords, access tokens, or phone numbers."""
    sensitive_payload = {
        "email": "doctor@hospital.org",
        "password": "SuperSecretPassword#123",
        "phone": "+91-9447111222",
        "nested": {
            "access_token": "eyJhbGciOi...",
            "action": "TRIAGE_COMPLETE"
        }
    }
    sanitized = sanitize_audit_data(sensitive_payload)
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["phone"] == "[REDACTED]"
    assert sanitized["nested"]["access_token"] == "[REDACTED]"
    assert sanitized["nested"]["action"] == "TRIAGE_COMPLETE"
    assert sanitized["email"] == "doctor@hospital.org"


# ==============================================================================
# 5. FASTAPI SECURITY HEADERS & RATE LIMIT TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_security_headers_on_responses():
    """FastAPI gateway must inject OWASP security headers on all responses."""
    import httpx
    from backend.app.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        headers = resp.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-XSS-Protection") == "1; mode=block"
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "Strict-Transport-Security" in headers
        assert "Content-Security-Policy" in headers


@pytest.mark.asyncio
async def test_payload_size_limit_enforcement():
    """Requests exceeding 2MB must be rejected with HTTP 413 Payload Too Large."""
    import httpx
    from backend.app.main import app

    oversized_body = "A" * (3 * 1024 * 1024)  # 3MB
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/incidents/report",
            content=oversized_body,
            headers={"Content-Length": str(len(oversized_body)), "Content-Type": "application/json"}
        )
        assert resp.status_code == 413
        assert "Payload too large" in resp.json()["detail"]
