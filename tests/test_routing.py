"""Tests for the business routing rules."""

from src.routing import apply_routing_rules, _has_unnegated_critical_term


def make_prediction(queue="Technical Support", queue_conf=0.8,
                    priority="medium", priority_conf=0.6):
    return {
        "queue": queue,
        "queue_confidence": queue_conf,
        "priority": priority,
        "priority_confidence": priority_conf,
    }


# --- critical term detection ---

def test_detects_critical_term():
    assert _has_unnegated_critical_term("the server outage began at noon")


def test_ignores_negated_term():
    assert not _has_unnegated_critical_term("this is not urgent at all")


def test_ignores_substring_matches():
    """'down' must not match inside 'download' or 'dropdown'."""
    assert not _has_unnegated_critical_term("the download failed silently")
    assert not _has_unnegated_critical_term("the dropdown menu is misaligned")


def test_no_term_present():
    assert not _has_unnegated_critical_term("i would like more documentation")


# --- escalation rule ---

def test_escalates_medium_to_high():
    result = apply_routing_rules(make_prediction(priority="medium"),
                                 "complete service outage")
    assert result["priority"] == "high"
    assert result["escalated"] is True
    assert result["model_priority"] == "medium"


def test_escalation_clears_stale_confidence():
    result = apply_routing_rules(make_prediction(priority="low"),
                                 "critical failure in production")
    assert result["priority_confidence"] is None


def test_rule_is_monotone_never_downgrades():
    """A high prediction stays high; rules can only raise priority."""
    result = apply_routing_rules(make_prediction(priority="high"),
                                 "just a small question")
    assert result["priority"] == "high"
    assert result["escalated"] is False


def test_negated_term_does_not_escalate():
    result = apply_routing_rules(make_prediction(priority="low"),
                                 "not urgent at all, just a suggestion")
    assert result["priority"] == "low"
    assert result["escalated"] is False


# --- triage rule ---

def test_low_confidence_goes_to_triage():
    result = apply_routing_rules(make_prediction(queue_conf=0.31), "some text")
    assert result["needs_triage"] is True
    assert result["assigned_queue"] == "Triage"


def test_triage_preserves_model_suggestion():
    result = apply_routing_rules(
        make_prediction(queue="IT Support", queue_conf=0.2), "some text"
    )
    assert result["assigned_queue"] == "Triage"
    assert result["queue"] == "IT Support"


def test_high_confidence_is_auto_routed():
    result = apply_routing_rules(
        make_prediction(queue="Billing and Payments", queue_conf=0.77), "text"
    )
    assert result["needs_triage"] is False
    assert result["assigned_queue"] == "Billing and Payments"