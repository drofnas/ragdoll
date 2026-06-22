from __future__ import annotations

from ragdoll.platform.db.models import User

from tests.modules._phase10_helpers import auth_headers, default_space, register_and_login, seed_retrieval_document


def test_chat_routes_require_authentication(api_client):
    create = api_client.post("/api/v1/chat/sessions")
    listing = api_client.get("/api/v1/chat/sessions")
    assert create.status_code == 401
    assert listing.status_code == 401


def test_chat_session_message_flow_returns_citations_and_degraded_answer(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    seed_retrieval_document(
        db_session,
        space=default_space(db_session, owner),
        uploader=owner,
        title="atlas.txt",
        text="Atlas is the primary project for the workspace.",
        entity_specs=[("Atlas", "project")],
    )

    created = api_client.post("/api/v1/chat/sessions", headers=auth_headers(token))
    assert created.status_code == 200, created.text
    session_id = created.json()["id"]

    message = api_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "Tell me about Atlas"},
    )
    assert message.status_code == 200, message.text
    payload = message.json()
    assert payload["assistant_message"]["degraded"] is True
    assert payload["assistant_message"]["retrieval_mode"] == "combined"
    assert payload["assistant_message"]["citations"]
    assert "Atlas" in payload["assistant_message"]["content"]
    assert payload["session"]["title"].startswith("Tell me about Atlas")


def test_verified_correction_appears_in_later_chat_answer(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    seed_retrieval_document(
        db_session,
        space=default_space(db_session, owner),
        uploader=owner,
        title="status.txt",
        text="Atlas is listed as active in the project notes.",
        entity_specs=[("Atlas", "project")],
    )

    session_response = api_client.post("/api/v1/chat/sessions", headers=auth_headers(token))
    session_id = session_response.json()["id"]

    correction = api_client.post(
        "/api/v1/corrections",
        headers=auth_headers(token),
        json={
            "chat_session_id": session_id,
            "proposed_value": "Atlas is paused",
            "rationale": "atlas paused",
        },
    )
    assert correction.status_code == 200, correction.text
    correction_id = correction.json()["id"]

    verify = api_client.post(
        f"/api/v1/corrections/{correction_id}/verify",
        headers=auth_headers(token),
        json={"review_notes": "confirmed"},
    )
    assert verify.status_code == 200, verify.text

    message = api_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "Is Atlas paused?"},
    )
    assert message.status_code == 200, message.text
    assert "Atlas is paused" in message.json()["assistant_message"]["content"]
