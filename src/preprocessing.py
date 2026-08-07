"""Text preprocessing shared between model training and API inference.

This module is the single source of truth for text normalization.
Both the training notebooks and the Flask inference endpoint import
from here, guaranteeing identical treatment of a ticket in both contexts.
"""

import re

URL_RE = re.compile(r"https?://\S+|www\.\S+")
EMAIL_RE = re.compile(r"\S+@\S+\.\S+")
PLACEHOLDER_RE = re.compile(r"<[^>]+>|\{[^}]+\}|\[[^\]]+\]")
NON_ALPHA_RE = re.compile(r"[^a-z\s]")
MULTI_SPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """Normalize raw ticket text into a lowercase alphabetic token stream."""
    if not isinstance(text, str):
        return ""

    text = text.lower()
    text = URL_RE.sub(" ", text)
    text = EMAIL_RE.sub(" ", text)
    text = PLACEHOLDER_RE.sub(" ", text)
    text = NON_ALPHA_RE.sub(" ", text)
    text = MULTI_SPACE_RE.sub(" ", text)
    return text.strip()


def build_ticket_text(subject: str, body: str) -> str:
    """Combine subject and body into the single field the models consume."""
    subject = subject if isinstance(subject, str) else ""
    body = body if isinstance(body, str) else ""
    return clean_text(f"{subject} {body}")