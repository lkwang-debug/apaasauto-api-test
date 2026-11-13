import base64
import hashlib
import hmac
import json
import time


def base64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def quick_generate_jwt(app_key, app_secret):
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"appKey": app_key, "timestamp": int(time.time())}

    encoded_header = base64url_encode(json.dumps(header).encode("utf-8"))
    encoded_payload = base64url_encode(json.dumps(payload).encode("utf-8"))
    signature = hmac.new(
        app_secret.encode("utf-8"),
        encoded_header + b"." + encoded_payload,
        hashlib.sha256,
    ).digest()
    encoded_signature = base64url_encode(signature)
    jwt_token = encoded_header + b"." + encoded_payload + b"." + encoded_signature
    return jwt_token.decode("utf-8")


def get_jwt_token(config):
    app_key = config.get("auth", "app_key", fallback="")
    app_secret = config.get("auth", "app_secret", fallback="")
    return quick_generate_jwt(app_key, app_secret)
