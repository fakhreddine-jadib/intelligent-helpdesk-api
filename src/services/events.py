"""In-process event broker for Server-Sent Events.

Publishers (ticket routes) push events; subscribers (SSE connections)
receive them through per-client queues. Broadcasting is fire-and-forget:
a slow or disconnected client never blocks the publisher.
"""

import json
import logging
import queue
import threading

logger = logging.getLogger(__name__)

MAX_QUEUE_SIZE = 50

_subscribers: set[queue.Queue] = set()
_lock = threading.Lock()


def subscribe() -> queue.Queue:
    """Register a new client and return its event queue."""
    q = queue.Queue(maxsize=MAX_QUEUE_SIZE)
    with _lock:
        _subscribers.add(q)
    logger.info("SSE client subscribed (%d active)", len(_subscribers))
    return q


def unsubscribe(q: queue.Queue) -> None:
    """Remove a client on disconnect."""
    with _lock:
        _subscribers.discard(q)
    logger.info("SSE client unsubscribed (%d active)", len(_subscribers))


def publish(event_type: str, payload: dict) -> None:
    """Broadcast an event to every connected client."""
    message = json.dumps({"type": event_type, "data": payload})
    with _lock:
        targets = list(_subscribers)

    for q in targets:
        try:
            q.put_nowait(message)
        except queue.Full:
            # client is not consuming fast enough; drop the event for it
            logger.warning("SSE queue full, dropping event for one client")


def subscriber_count() -> int:
    with _lock:
        return len(_subscribers)