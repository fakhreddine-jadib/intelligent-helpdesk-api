"""Request payload validation."""

MAX_SUBJECT_LENGTH = 300
MAX_BODY_LENGTH = 10000


def validate_ticket_payload(data) -> tuple[dict | None, dict | None]:
    """Validate an incoming ticket payload.

    Returns:
        (cleaned_payload, None) on success, or (None, error_dict) on failure.
    """
    if not isinstance(data, dict):
        return None, {"error": "invalid_payload",
                      "message": "Request body must be a JSON object."}

    subject = data.get("subject", "")
    body = data.get("body")

    if body is None:
        return None, {"error": "missing_field",
                      "message": "Field 'body' is required."}

    if not isinstance(subject, str) or not isinstance(body, str):
        return None, {"error": "invalid_type",
                      "message": "Fields 'subject' and 'body' must be strings."}

    subject, body = subject.strip(), body.strip()

    if not body:
        return None, {"error": "empty_body",
                      "message": "Field 'body' cannot be empty."}

    if len(subject) > MAX_SUBJECT_LENGTH:
        return None, {"error": "subject_too_long",
                      "message": f"Subject exceeds {MAX_SUBJECT_LENGTH} characters."}

    if len(body) > MAX_BODY_LENGTH:
        return None, {"error": "body_too_long",
                      "message": f"Body exceeds {MAX_BODY_LENGTH} characters."}

    return {"subject": subject, "body": body}, None