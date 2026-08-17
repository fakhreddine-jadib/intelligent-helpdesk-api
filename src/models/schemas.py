"""Document schemas for the MongoDB collections.

MongoDB is schemaless; these definitions document the intended structure
and are enforced by the application layer.
"""
from datetime import datetime, timezone

ROLES = ("client", "agent", "admin")

PRIORITIES = ("low", "medium", "high")

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}

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

def build_ticket_document(subject: str, body: str, prediction: dict,
                          author_id: str, author_email: str) -> dict:
    """Construct a ticket document enriched with model predictions."""
    now = utc_now()
    return {
        "subject": subject,
        "body": body,

        # author
        "author_id": author_id,
        "author_email": author_email,

        # raw model output (kept for auditability and retraining)
        "predicted_queue": prediction["queue"],
        "queue_confidence": prediction["queue_confidence"],
        "model_priority": prediction["priority"], 
        "priority_confidence": prediction.get("priority_confidence"),

        # routing decision
        "assigned_queue": prediction["assigned_queue"],
        "priority": prediction["priority"],
        "priority_rank": PRIORITY_RANK[prediction["priority"]],
        "escalated": prediction["escalated"],
        "needs_triage": prediction["needs_triage"],

        # workflow
        "status": "open",
        "assigned_agent_id": None,
        "created_at": now,
        "updated_at": now,
    }