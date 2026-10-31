"""
AES-256-GCM Application-Level Encryption Module for RESQ.
Provides authenticated encryption for sensitive PII, phone numbers, and medical data.
"""
import os
import base64
from typing import Optional, Dict
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class FieldEncryptionService:
    """
    AES-256-GCM Authenticated Encryption for sensitive fields.
    Format stored in DB:
    enc:v1:<base64(nonce_12bytes + ciphertext_with_16byte_tag)>
    """
    PREFIX = "enc:v"
    CURRENT_VERSION = 1

    def __init__(self, key_hex: Optional[str] = None):
        # Master key should be 32 bytes (256 bits) represented as 64-char hex string
        if not key_hex:
            key_hex = os.getenv("RESQ_MASTER_ENCRYPTION_KEY")

        if not key_hex:
            # Fallback for development/testing if not configured: predictable safe 32-byte key
            # In production, this must be provided via KMS / environment
            key_hex = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

        try:
            self._key = bytes.fromhex(key_hex)
            if len(self._key) != 32:
                raise ValueError("Master key must be exactly 32 bytes (256 bits)")
        except Exception as e:
            raise ValueError(f"Invalid encryption key format: {e}")

        # Active AESGCM instance
        self._aesgcm = AESGCM(self._key)

        # Key registry for key rotation support (version -> AESGCM)
        self._key_registry: Dict[int, AESGCM] = {
            self.CURRENT_VERSION: self._aesgcm
        }

    def encrypt(self, plaintext: Optional[str]) -> Optional[str]:
        """
        Encrypt a plaintext string using AES-256-GCM.
        Generates a cryptographically secure 12-byte (96-bit) nonce per invocation.
        Returns serialized string: enc:v1:<base64(nonce + ciphertext + tag)>
        """
        if plaintext is None or plaintext == "":
            return plaintext

        # Generate unique 96-bit nonce
        nonce = os.urandom(12)

        # Encrypt with authentication tag automatically appended by AESGCM
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

        # Pack nonce + ciphertext
        payload = nonce + ciphertext
        encoded = base64.b64encode(payload).decode("ascii")

        return f"{self.PREFIX}{self.CURRENT_VERSION}:{encoded}"

    def decrypt(self, ciphertext_str: Optional[str]) -> Optional[str]:
        """
        Decrypt a ciphertext string created by this service.
        If the string is plaintext (e.g. legacy records), returns it untouched.
        Verifies authentication tag and rejects tampered ciphertexts.
        """
        if ciphertext_str is None or ciphertext_str == "":
            return ciphertext_str

        # Check if text is encrypted with our prefix
        if not ciphertext_str.startswith(self.PREFIX):
            # Plaintext fallback for backward compatibility
            return ciphertext_str

        try:
            # Format: enc:v1:<base64>
            parts = ciphertext_str.split(":")
            if len(parts) != 3 or not parts[1].startswith("v"):
                raise ValueError("Invalid ciphertext structure")

            version_str = parts[1][1:]  # strip 'v'
            version = int(version_str)
            encoded_payload = parts[2]

            cipher = self._key_registry.get(version)
            if not cipher:
                raise ValueError(f"Unknown key version: {version}")

            raw_payload = base64.b64decode(encoded_payload.encode("ascii"))
            if len(raw_payload) < 28:  # 12-byte nonce + 16-byte tag minimum
                raise ValueError("Ciphertext payload too short")

            nonce = raw_payload[:12]
            ciphertext = raw_payload[12:]

            decrypted_bytes = cipher.decrypt(nonce, ciphertext, None)
            return decrypted_bytes.decode("utf-8")
        except Exception as e:
            # Re-raise as ValueError so caller knows decryption or tag verification failed
            raise ValueError(f"Decryption failed or ciphertext tampered: {e}")

    def is_encrypted(self, value: Optional[str]) -> bool:
        """Check if string is an encrypted ciphertext."""
        if not value:
            return False
        return value.startswith(self.PREFIX)


# Global singleton instance
field_crypto = FieldEncryptionService()
