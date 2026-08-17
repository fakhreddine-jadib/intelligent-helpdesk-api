"""Aggregate statistics for the agent dashboard."""

from flask import Blueprint, jsonify

from src.api.security import role_required
from src.db import get_db
from src.services.activity_log import MODEL_OVERRIDDEN

stats_bp = Blueprint("stats", __name__)


@stats_bp.get("/stats")
@role_required("agent", "admin")
def stats():
    """Return counts used by the dashboard summary cards."""
    db = get_db()

    def group_counts(field):
        pipeline = [{"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}}]
        return {doc["_id"]: doc["count"]
                for doc in db.tickets.aggregate(pipeline)}

    total = db.tickets.count_documents({})

    return jsonify({
        "total_tickets": total,
        "by_queue": group_counts("assigned_queue"),
        "by_priority": group_counts("priority"),
        "by_status": group_counts("status"),
        "pending_triage": db.tickets.count_documents(
            {"needs_triage": True, "status": "open"}),
        "open_high_priority": db.tickets.count_documents(
            {"priority": "high", "status": "open"}),
        "escalated_by_rule": db.tickets.count_documents({"escalated": True}),
    }), 200


@stats_bp.get("/stats/model")
@role_required("admin")
def model_stats():
    """Production model performance, measured against agent corrections."""
    db = get_db()

    total = db.tickets.count_documents({})
    if total == 0:
        return jsonify({"total_tickets": 0,
                        "message": "No tickets recorded yet."}), 200

    auto_routed = db.tickets.count_documents({"needs_triage": False})
    rerouted = db.tickets.count_documents({"manually_rerouted": True})
    reprioritized = db.tickets.count_documents({"manually_reprioritized": True})
    overrides = db.logs.count_documents({"event_type": MODEL_OVERRIDDEN})

    # mean confidence of automatically routed tickets
    pipeline = [
        {"$match": {"needs_triage": False}},
        {"$group": {"_id": None, "avg": {"$avg": "$queue_confidence"}}},
    ]
    agg = list(db.tickets.aggregate(pipeline))
    avg_conf = round(agg[0]["avg"], 4) if agg else None

    return jsonify({
        "total_tickets": total,
        "auto_routed": auto_routed,
        "auto_routed_rate": round(auto_routed / total, 4),
        "sent_to_triage": total - auto_routed,
        "manually_rerouted": rerouted,
        "manually_reprioritized": reprioritized,
        "override_events": overrides,
        "observed_routing_error_rate": (
            round(rerouted / auto_routed, 4) if auto_routed else None),
        "mean_confidence_auto_routed": avg_conf,
    }), 200