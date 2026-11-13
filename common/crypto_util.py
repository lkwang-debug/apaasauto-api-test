import hashlib
from typing import Any

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


SENSITIVE_FIELD_NAMES = {"password", "chairPassword", "userPwd", "roomPwd"}


def aes256_encrypt_hex(value: str, app_key: str, app_secret: str) -> str:
    secret_source = f"{app_key}{app_secret}"
    digest_hex = hashlib.sha256(secret_source.encode("utf-8")).hexdigest()
    key = digest_hex[:32].encode("utf-8")
    iv = digest_hex[32:48].encode("utf-8")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(value.encode("utf-8"), AES.block_size))
    return encrypted.hex().upper()


def encrypt_sensitive_fields(payload: Any, app_key: str, app_secret: str):
    if isinstance(payload, dict):
        encrypted = {}
        for key, value in payload.items():
            if key in SENSITIVE_FIELD_NAMES and isinstance(value, str) and value != "":
                encrypted[key] = aes256_encrypt_hex(value, app_key, app_secret)
            else:
                encrypted[key] = encrypt_sensitive_fields(value, app_key, app_secret)
        return encrypted

    if isinstance(payload, list):
        return [encrypt_sensitive_fields(item, app_key, app_secret) for item in payload]

    return payload
