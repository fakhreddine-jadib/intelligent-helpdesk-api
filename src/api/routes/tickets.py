"""Ticket CRUD endpoints."""

import logging

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, jsonify, request

from src.api.security import token_required, role_required
from src.api.validators import validate_ticket_payload
from src.db import get_db
from src.inference import predict_ticket
from src.models.schemas import (build_ticket_document, utc_now,
                                TICKET_STATUSES, QUEUES, PRIORITIES,
                                PRIORITY_RANK)
from src.services import activity_log

logger = logging.getLogger(__name__)

tickets_bp = Blueprint("tickets", __name__)

MAX_PAGE_SIZE = 100


def _serialize(doc: dict) -> dict:
    """Convert a MongoDB document into a JSON-safe dict."""
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    for field in ("created_at", "updated_at"):
        if doc.get(field):
            doc[field] = doc[field].isoformat()
    if doc.get("assigned_agent_id"):
        doc["assigned_agent_id"] = str(doc["assigned_agent_id"])
    return doc


@tickets_bp.post("/tickets")
@token_required
def create_ticket():
    """Submit a ticket: classify it, route it, and persist it."""
    payload, error = validate_ticket_payload(request.get_json(silent=True))
    if error:
        return jsonify(error), 400

    prediction = predict_ticket(payload["subject"], payload["body"])
    if "error" in prediction:
        return jsonify(prediction), 422

    user = request.current_user
    document = build_ticket_document(
        subject=payload["subject"],
        body=payload["body"],
        prediction=prediction,
        author_id=user["sub"],
        author_email=user["email"],
    )

    db = get_db()
    result = db.tickets.insert_one(document)
    document["_id"] = result.inserted_id

    logger.info("Ticket %s created -> %s / %s (triage=%s)",
                result.inserted_id, document["assigned_queue"],
                document["priority"], document["needs_triage"])
    
    activity_log.record(
        activity_log.TICKET_CREATED,
        actor_email=user["email"],
        ticket_id=str(result.inserted_id),
        details={
            "assigned_queue": document["assigned_queue"],
            "priority": document["priority"],
            "needs_triage": document["needs_triage"],
            "escalated": document["escalated"],
        },
    )

    return jsonify(_serialize(document)), 201


@tickets_bp.get("/tickets")
@token_required
def list_tickets():
    """List tickets, filtered by role and optional query parameters."""
    db = get_db()
    user = request.current_user

    query = {}

    # clients only ever see their own tickets
    if user["role"] == "client":
        query["author_id"] = user["sub"]

    queue = request.args.get("queue")
    if queue:
        if queue not in QUEUES:
            return jsonify({"error": "invalid_queue",
                            "message": f"Unknown queue '{queue}'."}), 400
        query["assigned_queue"] = queue

    priority = request.args.get("priority")
    if priority:
        if priority not in PRIORITIES:
            return jsonify({"error": "invalid_priority",
                            "message": f"Unknown priority '{priority}'."}), 400
        query["priority"] = priority

    status = request.args.get("status")
    if status:
        if status not in TICKET_STATUSES:
            return jsonify({"error": "invalid_status",
                            "message": f"Unknown status '{status}'."}), 400
        query["status"] = status

    try:
        page = max(1, int(request.args.get("page", 1)))
        page_size = min(MAX_PAGE_SIZE, max(1, int(request.args.get("page_size", 20))))
    except ValueError:
        return jsonify({"error": "invalid_pagination",
                        "message": "Parameters 'page' and 'page_size' must be integers."}), 400

    total = db.tickets.count_documents(query)
    cursor = (db.tickets.find(query)
              .sort([("priority_rank", 1), ("created_at", -1)])
              .skip((page - 1) * page_size)
              .limit(page_size))

    return jsonify({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize(d) for d in cursor],
    }), 200


@tickets_bp.get("/tickets/<ticket_id>")
@token_required
def get_ticket(ticket_id):
    """Retrieve a single ticket."""
    db = get_db()
    try:
        doc = db.tickets.find_one({"_id": ObjectId(ticket_id)})
    except InvalidId:
        return jsonify({"error": "invalid_id",
                        "message": "Malformed ticket identifier."}), 400

    if not doc:
        return jsonify({"error": "not_found",
                        "message": "Ticket does not exist."}), 404

    user = request.current_user
    if user["role"] == "client" and doc["author_id"] != user["sub"]:
        return jsonify({"error": "forbidden",
                        "message": "You cannot access this ticket."}), 403

    return jsonify(_serialize(doc)), 200


@tickets_bp.patch("/tickets/<ticket_id>")
@role_required("agent", "admin")
def update_ticket(ticket_id):
    """Update a ticket's status, queue, priority or assignee (agents only)."""
    data = request.get_json(silent=True) or {}
    updates = {}

    if "status" in data:
        if data["status"] not in TICKET_STATUSES:
            return jsonify({"error": "invalid_status",
                            "message": f"Status must be one of {TICKET_STATUSES}."}), 400
        updates["status"] = data["status"]

    if "assigned_queue" in data:
        if data["assigned_queue"] not in QUEUES:
            return jsonify({"error": "invalid_queue",
                            "message": f"Unknown queue '{data['assigned_queue']}'."}), 400
        updates["assigned_queue"] = data["assigned_queue"]
        updates["needs_triage"] = False
        updates["manually_rerouted"] = True

    if "priority" in data:
        if data["priority"] not in PRIORITIES:
            return jsonify({"error": "invalid_priority",
                            "message": f"Priority must be one of {PRIORITIES}."}), 400
        updates["priority"] = data["priority"]
        updates["priority_rank"] = PRIORITY_RANK[data["priority"]]
        updates["manually_reprioritized"] = True

    if "assigned_agent_id" in data:
        updates["assigned_agent_id"] = data["assigned_agent_id"]

    if not updates:
        return jsonify({"error": "no_updates",
                        "message": "No valid field to update."}), 400

    updates["updated_at"] = utc_now()

    db = get_db()
    try:
        before = db.tickets.find_one({"_id": ObjectId(ticket_id)})
    except InvalidId:
        return jsonify({"error": "invalid_id",
                        "message": "Malformed ticket identifier."}), 400

    if not before:
        return jsonify({"error": "not_found",
                        "message": "Ticket does not exist."}), 404

    doc = db.tickets.find_one_and_update(
        {"_id": ObjectId(ticket_id)},
        {"$set": updates},
        return_document=True,
    )

    actor = request.current_user["email"]
    activity_log.record(
        activity_log.TICKET_UPDATED,
        actor_email=actor,
        ticket_id=ticket_id,
        details={"fields": list(updates.keys())},
    )
    activity_log.record_override(ticket_id, actor, before, updates)

    logger.info("Ticket %s updated by %s: %s",
                ticket_id, request.current_user["email"], list(updates))
    return jsonify(_serialize(doc)), 200


@tickets_bp.delete("/tickets/<ticket_id>")
@role_required("admin")
def delete_ticket(ticket_id):
    """Delete a ticket (administrators only)."""
    db = get_db()
    try:
        result = db.tickets.delete_one({"_id": ObjectId(ticket_id)})
    except InvalidId:
        return jsonify({"error": "invalid_id",
                        "message": "Malformed ticket identifier."}), 400

    if result.deleted_count == 0:
        return jsonify({"error": "not_found",
                        "message": "Ticket does not exist."}), 404

    logger.warning("Ticket %s deleted by %s",
                   ticket_id, request.current_user["email"])
    
    activity_log.record(
        activity_log.TICKET_DELETED,
        actor_email=request.current_user["email"],
        ticket_id=ticket_id,
    )
    return jsonify({"deleted": True}), 200


@tickets_bp.get("/logs")
@role_required("admin")
def list_logs():
    """Read the activity log (administrators only)."""
    db = get_db()

    query = {}
    event_type = request.args.get("event_type")
    if event_type:
        query["event_type"] = event_type

    try:
        limit = min(200, max(1, int(request.args.get("limit", 50))))
    except ValueError:
        return jsonify({"error": "invalid_limit",
                        "message": "Parameter 'limit' must be an integer."}), 400

    cursor = db.logs.find(query).sort("timestamp", -1).limit(limit)

    items = []
    for doc in cursor:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        doc["timestamp"] = doc["timestamp"].isoformat()
        items.append(doc)

    return jsonify({"count": len(items), "items": items}), 200