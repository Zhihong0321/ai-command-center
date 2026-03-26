"""
Encryption service for the Secrets Vault.

Design:
- The unlock key is NEVER stored server-side.
- When saving: derive a Fernet key from the unlock key using PBKDF2HMAC + a random salt.
  Store: (encrypted_value, salt). Discard the unlock key immediately.
- When revealing: re-derive the same Fernet key from the unlock key + stored salt.
  If the unlock key is wrong, decryption raises InvalidToken (caught and returned as 403).
"""

import os
import base64
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


_ITERATIONS = 480_000  # OWASP 2024 recommendation for PBKDF2-SHA256


def _derive_key(unlock_key: str, salt: bytes) -> bytes:
    """Derive a 32-byte Fernet key from an unlock key + salt using PBKDF2-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(unlock_key.encode("utf-8")))


def encrypt_secret(plaintext: str, unlock_key: str) -> tuple[str, str]:
    """
    Encrypt a plaintext secret with the given unlock key.

    Returns:
        (encrypted_b64: str, salt_b64: str)
        Both are base64-encoded strings safe to store in the DB.
    """
    salt = os.urandom(16)
    fernet_key = _derive_key(unlock_key, salt)
    f = Fernet(fernet_key)
    encrypted = f.encrypt(plaintext.encode("utf-8"))
    return (
        base64.urlsafe_b64encode(encrypted).decode("utf-8"),
        base64.urlsafe_b64encode(salt).decode("utf-8"),
    )


def decrypt_secret(encrypted_b64: str, salt_b64: str, unlock_key: str) -> str:
    """
    Decrypt a stored secret using the unlock key.

    Raises:
        ValueError: if the unlock key is wrong or data is corrupted.
    """
    try:
        salt = base64.urlsafe_b64decode(salt_b64.encode("utf-8"))
        fernet_key = _derive_key(unlock_key, salt)
        f = Fernet(fernet_key)
        encrypted = base64.urlsafe_b64decode(encrypted_b64.encode("utf-8"))
        return f.decrypt(encrypted).decode("utf-8")
    except (InvalidToken, Exception):
        raise ValueError("Invalid unlock key. Cannot decrypt secret.")
