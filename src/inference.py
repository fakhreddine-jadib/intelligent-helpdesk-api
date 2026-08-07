"""Real-time ticket inference.

Loads the trained artifacts once at import time and exposes a single
prediction entry point. Imported by the Flask API; also usable standalone.

Pipeline:
    raw subject + body
        -> build_ticket_text()      (src.preprocessing)
        -> TF-IDF vectorization
        -> queue classifier + priority classifier
        -> apply_routing_rules()    (src.routing)
        -> final routing decision
"""

from pathlib import Path
import joblib

from src.preprocessing import build_ticket_text
from src.routing import apply_routing_rules

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

_vectorizer = joblib.load(MODELS_DIR / "tfidf_vectorizer.joblib")
_queue_clf = joblib.load(MODELS_DIR / "queue_classifier.joblib")
_priority_clf = joblib.load(MODELS_DIR / "priority_classifier.joblib")

MIN_WORDS = 3


def _top_prediction(classifier, matrix):
    """Return the predicted label and its probability."""
    proba = classifier.predict_proba(matrix)[0]
    idx = proba.argmax()
    return str(classifier.classes_[idx]), float(proba[idx])


def predict_ticket(subject: str, body: str) -> dict:
    """Predict department and priority for a single ticket.

    Args:
        subject: Raw ticket subject line.
        body: Raw ticket body text.

    Returns:
        A JSON-serializable dict containing the model predictions and the
        final routing decision, or an error dict if the text is too short
        to classify reliably.
    """
    text = build_ticket_text(subject, body)

    if len(text.split()) < MIN_WORDS:
        return {
            "error": "text_too_short",
            "message": "Ticket text is too short to classify reliably.",
        }

    matrix = _vectorizer.transform([text])

    queue, queue_conf = _top_prediction(_queue_clf, matrix)
    priority, priority_conf = _top_prediction(_priority_clf, matrix)

    prediction = {
        "queue": queue,
        "queue_confidence": round(queue_conf, 4),
        "priority": priority,
        "priority_confidence": round(priority_conf, 4),
    }

    return apply_routing_rules(prediction, text)