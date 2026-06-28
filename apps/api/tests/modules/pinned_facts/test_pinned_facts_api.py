from __future__ import annotations

from ragdoll.platform.db.models import User

from tests.modules._phase10_helpers import auth_headers, default_space, register_and_login, seed_retrieval_document


def _create_fact(api_client, token: str, *, title: str = "Focus Project", description: str = "Atlas"):
    return api_client.post(
        "/api/v1/pinned-facts",
        headers=auth_headers(token),
        json={
            "key": "focus_project",
            "title": title,
            "description": description,
            "value_kind": "text",
            "value_text": "Atlas",
            "confidence": 0.95,
            "evidence": [
                {
                    "quote": "Atlas is the current focus project.",
                    "citations": [],
                    "source_chunk_ids": [],
                }
            ],
        },
    )


def test_pinned_facts_require_authentication(api_client):
    response = api_client.get("/api/v1/pinned-facts")
    assert response.status_code == 401


def test_create_pinned_fact_and_read_history(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    response = _create_fact(api_client, token)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["title"] == "Focus Project"
    assert payload["value_text"] == "Atlas"
    assert payload["status"] == "active"
    assert payload["history_count"] == 1

    history = api_client.get(f"/api/v1/pinned-facts/{payload['id']}/history", headers=auth_headers(token))
    assert history.status_code == 200, history.text
    assert history.json()["items"][0]["reason"] == "created"


def test_verified_correction_updates_pinned_fact(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    created = _create_fact(api_client, token)
    fact_id = created.json()["id"]

    correction = api_client.post(
        "/api/v1/corrections",
        headers=auth_headers(token),
        json={
            "pinned_fact_id": fact_id,
            "proposed_value": "Northstar",
            "rationale": "verified rename",
        },
    )
    assert correction.status_code == 200, correction.text

    verified = api_client.post(
        f"/api/v1/corrections/{correction.json()['id']}/verify",
        headers=auth_headers(token),
        json={"review_notes": "confirmed"},
    )
    assert verified.status_code == 200, verified.text

    detail = api_client.get(f"/api/v1/pinned-facts/{fact_id}", headers=auth_headers(token))
    assert detail.status_code == 200, detail.text
    assert detail.json()["value_text"] == "Northstar"


def test_recheck_creates_conflict_candidates(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    space = default_space(db_session, owner)
    seed_retrieval_document(
        db_session,
        space=space,
        uploader=owner,
        title="atlas.txt",
        text="Atlas is a major project.",
        entity_specs=[("Atlas", "project")],
    )
    seed_retrieval_document(
        db_session,
        space=space,
        uploader=owner,
        title="zephyr.txt",
        text="Zephyr is another major project.",
        entity_specs=[("Zephyr", "project")],
    )

    created = api_client.post(
        f"/api/v1/pinned-facts?space_id={space.id}",
        headers=auth_headers(token),
        json={
            "key": "major_project",
            "title": "Major Project",
            "description": "project",
            "entity_type_hint": "project",
            "value_kind": "text",
            "value_text": "Atlas",
            "confidence": 0.9,
            "evidence": [{"quote": "Atlas is a major project.", "citations": [], "source_chunk_ids": []}],
        },
    )
    assert created.status_code == 200, created.text
    fact_id = created.json()["id"]

    rechecked = api_client.post(
        f"/api/v1/pinned-facts/{fact_id}/recheck?space_id={space.id}",
        headers=auth_headers(token),
    )
    assert rechecked.status_code == 200, rechecked.text
    assert rechecked.json()["status"] == "conflicted"

    candidates = api_client.get(
        f"/api/v1/pinned-facts/{fact_id}/candidates?space_id={space.id}",
        headers=auth_headers(token),
    )
    assert candidates.status_code == 200, candidates.text
    assert len(candidates.json()["items"]) >= 2


def test_revert_restores_an_older_version_as_new_current_value(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    created = _create_fact(api_client, token)
    fact_id = created.json()["id"]

    correction = api_client.post(
        "/api/v1/corrections",
        headers=auth_headers(token),
        json={
            "pinned_fact_id": fact_id,
            "proposed_value": "Northstar",
            "rationale": "verified rename",
        },
    )
    api_client.post(
        f"/api/v1/corrections/{correction.json()['id']}/verify",
        headers=auth_headers(token),
        json={"review_notes": "confirmed"},
    )

    history = api_client.get(f"/api/v1/pinned-facts/{fact_id}/history", headers=auth_headers(token)).json()["items"]
    created_entry = next(item for item in history if item["reason"] == "created")
    reverted = api_client.post(
        f"/api/v1/pinned-facts/{fact_id}/history/{created_entry['id']}/revert",
        headers=auth_headers(token),
    )
    assert reverted.status_code == 200, reverted.text
    assert reverted.json()["value_text"] == "Atlas"

    refreshed_history = api_client.get(f"/api/v1/pinned-facts/{fact_id}/history", headers=auth_headers(token))
    assert refreshed_history.status_code == 200, refreshed_history.text
    assert any(item["reason"] == "user_reverted" for item in refreshed_history.json()["items"])
