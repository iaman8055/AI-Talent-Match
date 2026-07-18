import hashlib
import secrets

_RAW_TOKEN_BYTES = 48


def generate_raw_token() -> str:
    return secrets.token_urlsafe(_RAW_TOKEN_BYTES)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()
