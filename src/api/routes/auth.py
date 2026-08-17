"""Registration and login endpoints."""

import logging
import re

from flask import Blueprint, jsonify, request
from pymongo.errors import DuplicateKeyError

from src.api.security import (hash_password, verify_password,
                              generate_token, token_required)
from src.db import get_db
from src.models.schemas import build_user_document, ROLES

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


def _validate_registration(data):
    """Validate a registration payload."""
    if not isinstance(data, dict):
        return None, {"error": "invalid_payload",
                      "message": "Request body must be a JSON object."}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()
    role = (data.get("role") or "client").strip()

    if not EMAIL_RE.match(email):
        return None, {"error": "invalid_email",
                      "message": "A valid email address is required."}

    if len(password) < MIN_PASSWORD_LENGTH:
        return None, {"error": "weak_password",
                      "message": f"Password must be at least "
                                 f"{MIN_PASSWORD_LENGTH} characters."}

    if not full_name:
        return None, {"error": "missing_name",
                      "message": "Field 'full_name' is required."}

    if role not in ROLES:
        return None, {"error": "invalid_role",
                      "message": f"Role must be one of {ROLES}."}

    return {"email": email, "password": password,
            "full_name": full_name, "role": role}, None


@auth_bp.post("/auth/register")
def register():
    """Create a new user account."""
    payload, error = _validate_registration(request.get_json(silent=True))
    if error:
        return jsonify(error), 400

    db = get_db()
    document = build_user_document(
        email=payload["email"],
        password_hash=hash_password(payload["password"]),
        full_name=payload["full_name"],
        role=payload["role"],
    )

    try:
        result = db.users.insert_one(document)
    except DuplicateKeyError:
        return jsonify({"error": "email_taken",
                        "message": "An account with this email already exists."}), 409

    logger.info("User registered: %s (%s)", payload["email"], payload["role"])
    return jsonify({
        "id": str(result.inserted_id),
        "email": payload["email"],
        "full_name": payload["full_name"],
        "role": payload["role"],
    }), 201


@auth_bp.post("/auth/login")
def login():
    """Authenticate a user and issue a JWT."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "missing_credentials",
                        "message": "Email and password are required."}), 400

    db = get_db()
    user = db.users.find_one({"email": email})

    if not user or not verify_password(password, user["password_hash"]):
        logger.warning("Failed login attempt for %s", email)
        return jsonify({"error": "invalid_credentials",
                        "message": "Incorrect email or password."}), 401

    if not user.get("is_active", True):
        return jsonify({"error": "account_disabled",
                        "message": "This account has been disabled."}), 403

    token = generate_token(user["_id"], user["email"], user["role"])
    return jsonify({
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
        },
    }), 200


@auth_bp.get("/auth/me")
@token_required
def me():
    """Return the authenticated user's profile."""
    return jsonify({
        "id": request.current_user["sub"],
        "email": request.current_user["email"],
        "role": request.current_user["role"],
    }), 200