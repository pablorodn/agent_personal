import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

IV_LENGTH = 12


def _get_key() -> bytes:
    hex_key = os.environ["OAUTH_ENCRYPTION_KEY"]
    if len(hex_key) != 64:
        raise ValueError("OAUTH_ENCRYPTION_KEY must be 64 hex chars (32 bytes)")
    return bytes.fromhex(hex_key)


def encrypt(plaintext: str) -> str:
    key = _get_key()
    iv = os.urandom(IV_LENGTH)
    aesgcm = AESGCM(key)
    ct_with_tag = aesgcm.encrypt(iv, plaintext.encode(), None)
    ciphertext = ct_with_tag[:-16]
    auth_tag = ct_with_tag[-16:]
    return f"{iv.hex()}:{auth_tag.hex()}:{ciphertext.hex()}"


def decrypt(encoded: str) -> str:
    key = _get_key()
    iv_hex, auth_tag_hex, ciphertext_hex = encoded.split(":")
    iv = bytes.fromhex(iv_hex)
    auth_tag = bytes.fromhex(auth_tag_hex)
    ciphertext = bytes.fromhex(ciphertext_hex)
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(iv, ciphertext + auth_tag, None)
    return plaintext.decode()
