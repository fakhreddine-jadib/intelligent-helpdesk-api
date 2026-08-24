"""Tests for the shared text preprocessing module."""

from src.preprocessing import clean_text, build_ticket_text


def test_lowercases():
    assert clean_text("URGENT Problem") == "urgent problem"


def test_strips_urls():
    out = clean_text("see https://example.com/page for details")
    assert "http" not in out and "example" not in out


def test_strips_emails():
    out = clean_text("contact support@company.com now")
    assert "@" not in out and "company" not in out


def test_strips_generator_placeholders():
    out = clean_text("Hello <name>, your {product} order [id] shipped")
    assert "<" not in out and "{" not in out and "[" not in out


def test_strips_digits_and_punctuation():
    assert clean_text("Order #12345 failed!") == "order failed"


def test_collapses_whitespace():
    assert clean_text("too    many\n\nspaces") == "too many spaces"


def test_handles_non_string_input():
    assert clean_text(None) == ""
    assert clean_text(42) == ""


def test_build_ticket_text_concatenates():
    assert build_ticket_text("Login issue", "Cannot access account") == (
        "login issue cannot access account"
    )


def test_build_ticket_text_tolerates_missing_subject():
    assert build_ticket_text(None, "Server is down") == "server is down"