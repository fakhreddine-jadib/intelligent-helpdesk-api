"""Tests for ticket CRUD and role-based access control."""

OUTAGE = {
    "subject": "Server outage",
    "body": "Our production servers have been completely down for two hours. "
            "All customers are affected and we cannot process transactions.",
}

BILLING = {
    "subject": "Invoice question",
    "body": "I noticed a charge on my monthly invoice that I do not recognize. "
            "Could you please clarify what this line item refers to?",
}


def test_create_ticket_returns_prediction(client, client_headers):
    res = client.post("/api/tickets", json=OUTAGE, headers=client_headers)
    assert res.status_code == 201
    body = res.get_json()
    assert body["assigned_queue"]
    assert body["priority"] in ("low", "medium", "high")
    assert body["status"] == "open"


def test_create_requires_authentication(client):
    assert client.post("/api/tickets", json=OUTAGE).status_code == 401


def test_missing_body_rejected(client, client_headers):
    res = client.post("/api/tickets", json={"subject": "x"},
                      headers=client_headers)
    assert res.status_code == 400


def test_short_text_rejected(client, client_headers):
    res = client.post("/api/tickets", json={"subject": "help", "body": "now"},
                      headers=client_headers)
    assert res.status_code == 422


def test_oversized_body_rejected(client, client_headers):
    res = client.post("/api/tickets",
                      json={"subject": "x", "body": "word " * 5000},
                      headers=client_headers)
    assert res.status_code == 400


def test_client_sees_only_own_tickets(client, client_headers, agent_headers):
    client.post("/api/tickets", json=OUTAGE, headers=client_headers)

    # a second client
    client.post("/api/auth/register", json={
        "email": "other@test.local", "password": "password123",
        "full_name": "Other", "role": "client",
    })
    token = client.post("/api/auth/login", json={
        "email": "other@test.local", "password": "password123",
    }).get_json()["token"]
    other = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/tickets", headers=other).get_json()["total"] == 0
    assert client.get("/api/tickets", headers=client_headers).get_json()["total"] == 1


def test_agent_sees_all_tickets(client, client_headers, agent_headers):
    client.post("/api/tickets", json=OUTAGE, headers=client_headers)
    client.post("/api/tickets", json=BILLING, headers=client_headers)
    assert client.get("/api/tickets", headers=agent_headers).get_json()["total"] == 2


def test_sorted_by_priority(client, client_headers, agent_headers):
    client.post("/api/tickets", json=BILLING, headers=client_headers)
    client.post("/api/tickets", json=OUTAGE, headers=client_headers)

    items = client.get("/api/tickets", headers=agent_headers).get_json()["items"]
    ranks = [{"high": 0, "medium": 1, "low": 2}[t["priority"]] for t in items]
    assert ranks == sorted(ranks), "queue must be ordered by urgency"


def test_client_cannot_update(client, client_headers):
    tid = client.post("/api/tickets", json=OUTAGE,
                      headers=client_headers).get_json()["id"]
    res = client.patch(f"/api/tickets/{tid}", json={"status": "resolved"},
                       headers=client_headers)
    assert res.status_code == 403


def test_agent_can_update(client, client_headers, agent_headers):
    tid = client.post("/api/tickets", json=OUTAGE,
                      headers=client_headers).get_json()["id"]
    res = client.patch(f"/api/tickets/{tid}",
                       json={"status": "in_progress", "assigned_queue": "IT Support"},
                       headers=agent_headers)
    assert res.status_code == 200
    body = res.get_json()
    assert body["status"] == "in_progress"
    assert body["manually_rerouted"] is True
    assert body["needs_triage"] is False


def test_invalid_queue_rejected(client, client_headers, agent_headers):
    tid = client.post("/api/tickets", json=OUTAGE,
                      headers=client_headers).get_json()["id"]
    res = client.patch(f"/api/tickets/{tid}",
                       json={"assigned_queue": "Nonexistent Department"},
                       headers=agent_headers)
    assert res.status_code == 400


def test_agent_cannot_delete(client, client_headers, agent_headers):
    tid = client.post("/api/tickets", json=OUTAGE,
                      headers=client_headers).get_json()["id"]
    assert client.delete(f"/api/tickets/{tid}",
                         headers=agent_headers).status_code == 403


def test_admin_can_delete(client, client_headers, admin_headers):
    tid = client.post("/api/tickets", json=OUTAGE,
                      headers=client_headers).get_json()["id"]
    assert client.delete(f"/api/tickets/{tid}",
                         headers=admin_headers).status_code == 200


def test_malformed_id_rejected(client, agent_headers):
    res = client.get("/api/tickets/not-an-object-id", headers=agent_headers)
    assert res.status_code == 400


def test_override_is_logged(client, client_headers, agent_headers, admin_headers):
    tid = client.post("/api/tickets", json=OUTAGE,
                      headers=client_headers).get_json()["id"]
    client.patch(f"/api/tickets/{tid}",
                 json={"assigned_queue": "Human Resources"},
                 headers=agent_headers)

    logs = client.get("/api/logs?event_type=model_overridden",
                      headers=admin_headers).get_json()
    assert logs["count"] >= 1
    assert logs["items"][0]["details"]["queue"]["agent_assigned"] == "Human Resources"