"""Activity logging for auditability and model monitoring.

Records significant events in the tickets lifecycle. Beyond audit needs,
the log of agent overrides constitutes the raw material for measuring
model performance in production.
"""

import logging

from src.db import get_db
from src.models.schemas import utc_now

logger = logging.getLogger(__name__)

# event types
TICKET_CREATED = "ticket_created"
TICKET_UPDATED = "ticket_updated"
TICKET_DELETED = "ticket_deleted"
MODEL_OVERRIDDEN = "model_overridden"
USER_REGISTERED = "user_registered"
LOGIN_FAILED = "login_failed"


def record(event_type: str, actor_email: str | None = None,
           ticket_id: str | None = None, details: dict | None = None) -> None:
    """Write an entry to the activity log.

    Logging failures never propagate: an audit trail problem must not
    break the user-facing operation that triggered it.
    """
    try:
        get_db().logs.insert_one({
            "event_type": event_type,
            "actor_email": actor_email,
            "ticket_id": ticket_id,
            "details": details or {},
            "timestamp": utc_now(),
        })
    except Exception:
        logger.exception("Failed to write activity log entry")


def record_override(ticket_id: str, actor_email: str,
                    before: dict, after: dict) -> None:
    """Record an agent correction of a model prediction.

    Only fields the model itself predicted are tracked, so the resulting
    log measures model error rather than ordinary workflow changes.
    """
    changes = {}

    if "assigned_queue" in after and after["assigned_queue"] != before.get("assigned_queue"):
        changes["queue"] = {
            "model_predicted": before.get("predicted_queue"),
            "model_confidence": before.get("queue_confidence"),
            "auto_assigned": before.get("assigned_queue"),
            "agent_assigned": after["assigned_queue"],
        }

    if "priority" in after and after["priority"] != before.get("priority"):
        changes["priority"] = {
            "model_predicted": before.get("model_priority"),
            "model_confidence": before.get("priority_confidence"),
            "was_escalated": before.get("escalated"),
            "agent_assigned": after["priority"],
        }

    if changes:
        record(MODEL_OVERRIDDEN, actor_email=actor_email,
               ticket_id=ticket_id, details=changes)