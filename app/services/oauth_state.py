import secrets


def build_oauth_state() -> str:
    return secrets.token_hex(16)
