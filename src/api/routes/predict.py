"""Ticket classification endpoint."""

import logging
import time

from flask import Blueprint, jsonify, request

from src.api.validators import validate_ticket_payload
from src.inference import predict_ticket

logger = logging.getLogger(__name__)

predict_bp = Blueprint("predict", __name__)


@predict_bp.post("/predict")
def predict():
    """Classify a ticket without persisting it.

    Request body:
        {"subject": "...", "body": "..."}

    Response:
        Model predictions enriched with the routing decision.
    """
    payload, error = validate_ticket_payload(request.get_json(silent=True))
    if error:
        return jsonify(error), 400

    started = time.perf_counter()
    result = predict_ticket(payload["subject"], payload["body"])
    elapsed_ms = (time.perf_counter() - started) * 1000

    if "error" in result:
        return jsonify(result), 422

    result["inference_time_ms"] = round(elapsed_ms, 2)
    logger.info(
        "Predicted queue=%s (%.2f) priority=%s triage=%s in %.2f ms",
        result["queue"], result["queue_confidence"],
        result["priority"], result["needs_triage"], elapsed_ms,
    )
    return jsonify(result), 200