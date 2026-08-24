"""Server-Sent Events stream for the agent dashboard."""

import logging
import queue

from flask import Blueprint, Response, request, stream_with_context

from src.api.security import decode_token
from src.services import events

logger = logging.getLogger(__name__)

events_bp = Blueprint("events", __name__)

HEARTBEAT_SECONDS = 20


@events_bp.get("/events")
def stream():
    """Open an SSE stream. Agents and administrators only.

    The token is passed as a query parameter because the browser's
    EventSource API cannot set custom headers.
    """
    token = request.args.get("token", "")
    payload = decode_token(token)

    if not payload:
        return {"error": "invalid_token",
                "message": "A valid token is required."}, 401

    if payload.get("role") not in ("agent", "admin"):
        return {"error": "forbidden",
                "message": "Insufficient permissions."}, 403

    def generate():
        q = events.subscribe()
        try:
            yield "retry: 3000\n\n"
            yield 'data: {"type": "connected"}\n\n'
            while True:
                try:
                    message = q.get(timeout=HEARTBEAT_SECONDS)
                    yield f"data: {message}\n\n"
                except queue.Empty:
                    # comment frame keeps proxies from closing an idle connection
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            pass
        finally:
            events.unsubscribe(q)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )