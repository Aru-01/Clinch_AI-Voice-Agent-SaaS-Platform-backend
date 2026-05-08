from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _get_cipher():
    """Return a Fernet cipher using the project ENCRYPTION_KEY."""
    key = settings.ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt_value(plain_text: str) -> str:
    """Encrypt a plain-text string and return a UTF-8 encoded ciphertext."""
    if not plain_text:
        return plain_text
    cipher = _get_cipher()
    return cipher.encrypt(plain_text.encode()).decode()


def decrypt_value(encrypted_text: str) -> str:
    """Decrypt a ciphertext string back to plain text."""
    if not encrypted_text:
        return encrypted_text
    try:
        cipher = _get_cipher()
        return cipher.decrypt(encrypted_text.encode()).decode()
    except (InvalidToken, Exception):
        return ""


def mask_value(plain_text: str, visible_chars: int = 4) -> str:
    """
    Return a masked version for safe frontend display.
    e.g. "sk-proj-abcdefgh" → "sk-p********************"
    """
    if not plain_text:
        return ""
    if len(plain_text) <= visible_chars:
        return "*" * len(plain_text)
    return plain_text[:visible_chars] + "*" * (len(plain_text) - visible_chars)
