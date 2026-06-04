from app.db.crypto import decrypt, encrypt


def test_encrypt_decrypt_roundtrip():
    token = "abc123"
    encoded = encrypt(token)
    decoded = decrypt(encoded)
    assert decoded == token


def test_crypto_format_is_three_parts():
    encoded = encrypt("token")
    assert len(encoded.split(":")) == 3
