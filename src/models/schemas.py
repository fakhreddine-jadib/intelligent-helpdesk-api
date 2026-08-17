"""Document schemas for the MongoDB collections.

MongoDB is schemaless; these definitions document the intended structure
and are enforced by the application layer.
"""

from datetime import datetime, timezone

ROLES = ("client", "agent", "admin")

PRIORITIES = ("low", "medium", "high")

TICKET_STATUSES = ("open", "in_progress", "resolved", "closed")

QUEUES = (
    "Billing and Payments",
    "Customer Service",
    "General Inquiry",
    "Human Resources",
    "IT Support",
    "Product Support",
    "Returns and Exchanges",
    "Sales and Pre-Sales",
    "Service Outages and Maintenance",
    "Technical Support",
    "Triage",
)


def utc_now():
    """Timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def build_user_document(email: str, password_hash: bytes,
                        full_name: str, role: str) -> dict:
    """Construct a user document."""
    return {
        "email": email.lower().strip(),
        "password_hash": password_hash,
        "full_name": full_name.strip(),
        "role": role,
        "created_at": utc_now(),
        "is_active": True,
    }