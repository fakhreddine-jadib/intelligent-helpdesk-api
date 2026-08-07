"""Real-time ticket inference.

Loads the trained artifacts once at import time and exposes a single
prediction entry point. Imported by the Flask API; also usable standalone.
"""

from pathlib import Path
import joblib

from src.preprocessing import build_ticket_text

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

_vectorizer = joblib.load(MODELS_DIR / "tfidf_vectorizer.joblib")
_queue_clf = joblib.load(MODELS_DIR / "queue_classifier.joblib")
_priority_clf = joblib.load(MODELS_DIR / "priority_classifier.joblib")


def _top_prediction(classifier, matrix):
    """Return the predicted label and its probability."""
    proba = classifier.predict_proba(matrix)[0]
    idx = proba.argmax()
    return str(classifier.classes_[idx]), float(proba[idx])


def predict_ticket(subject: str, body: str) -> dict:
    """Predict department and priority for a single ticket.

    Returns a dict ready to be serialized as JSON.
    """
    text = build_ticket_text(subject, body)

    if len(text.split()) < 3:
        return {
            "error": "text_too_short",
            "message": "Ticket text is too short to classify reliably.",
        }

    matrix = _vectorizer.transform([text])

    queue, queue_conf = _top_prediction(_queue_clf, matrix)
    priority, priority_conf = _top_prediction(_priority_clf, matrix)

    return {
        "queue": queue,
        "queue_confidence": round(queue_conf, 4),
        "priority": priority,
        "priority_confidence": round(priority_conf, 4),
    }