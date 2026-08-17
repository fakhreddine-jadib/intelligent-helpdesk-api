"""Password hashing and JWT token handling."""

from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
from flask import current_app, jsonify, request

TOKEN_EXPIRY_HOURS = 12


def hash_password(password: str) -> bytes:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def verify_password(password: str, password_hash: bytes) -> bool:
    """Check a plaintext password against its stored hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash)


def generate_token(user_id: str, email: str, role: str) -> str:
    """Issue a signed JWT for an authenticated user."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT. Returns None if invalid or expired."""
    try:
        return jwt.decode(token, current_app.config["SECRET_KEY"],
                          algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def _extract_token() -> str | None:
    """Read the bearer token from the Authorization header."""
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:]
    return None


def token_required(fn):
    """Reject requests without a valid JWT."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({"error": "missing_token",
                            "message": "Authorization header required."}), 401

        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "invalid_token",
                            "message": "Token is invalid or has expired."}), 401

        request.current_user = payload
        return fn(*args, **kwargs)
    return wrapper


def role_required(*allowed_roles):
    """Reject requests from users outside the allowed roles."""
    def decorator(fn):
        @wraps(fn)
        @token_required
        def wrapper(*args, **kwargs):
            if request.current_user.get("role") not in allowed_roles:
                return jsonify({"error": "forbidden",
                                "message": "Insufficient permissions."}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator