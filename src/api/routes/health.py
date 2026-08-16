"""Health and readiness endpoints."""

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    """Liveness probe — the process is running."""
    return jsonify({"status": "ok"})


@health_bp.get("/ready")
def ready():
    """Readiness probe — the ML models are loaded and usable."""
    try:
        from src.inference import _vectorizer, _queue_clf, _priority_clf
        return jsonify({
            "status": "ready",
            "models_loaded": True,
            "vocabulary_size": len(_vectorizer.vocabulary_),
            "queue_classes": list(_queue_clf.classes_),
            "priority_classes": list(_priority_clf.classes_),
        })
    except Exception as exc:
        return jsonify({
            "status": "not_ready",
            "models_loaded": False,
            "error": str(exc),
        }), 503