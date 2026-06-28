from __future__ import annotations

from ragdoll.platform.db.models import User

from tests.modules._phase10_helpers import auth_headers, default_space, register_and_login, seed_retrieval_document


def test_tracked_state_requires_authentication(api_client):
    fields = api_client.get("/api/v1/tracked-state/fields")
    summary = api_client.get("/api/v1/tracked-state/summary")
    assert fields.status_code == 401
    assert summary.status_code == 401


def test_tracked_state_resolves_from_retrieval_and_prefers_verified_correction(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    seed_retrieval_document(
        db_session,
        space=default_space(db_session, owner),
        uploader=owner,
        title="atlas.txt",
        text="Atlas is the current focus project.",
        entity_specs=[("Atlas", "project")],
    )

    created = api_client.post(
        "/api/v1/tracked-state/fields",
        headers=auth_headers(token),
        json={"key": "focus_project", "label": "Focus Project", "prompt": "Atlas", "entity_type_hint": "project"},
    )
    assert created.status_code == 200, created.text
    field_id = created.json()["id"]

    summary = api_client.get("/api/v1/tracked-state/summary", headers=auth_headers(token))
    assert summary.status_code == 200, summary.text
    first_item = summary.json()["items"][0]
    assert first_item["current_value"] == "Atlas"
    assert first_item["status"] == "resolved"

    correction = api_client.post(
        "/api/v1/corrections",
        headers=auth_headers(token),
        json={
            "tracked_field_id": field_id,
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

    recomputed = api_client.post(
        f"/api/v1/tracked-state/fields/{field_id}/recompute",
        headers=auth_headers(token),
        json={},
    )
    assert recomputed.status_code == 200, recomputed.text
    assert recomputed.json()["current_value"] == "Northstar"
    assert recomputed.json()["current_source_tier"] == "verified"


def test_tracked_state_conflicts_when_multiple_candidates_match(api_client, db_session):
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
        "/api/v1/tracked-state/fields",
        headers=auth_headers(token),
        json={"key": "major_project", "label": "Major Project", "prompt": "project", "entity_type_hint": "project"},
    )
    assert created.status_code == 200, created.text

    conflicts = api_client.get("/api/v1/tracked-state/conflicts", headers=auth_headers(token))
    assert conflicts.status_code == 200, conflicts.text
    assert conflicts.json()["items"]
    assert len(conflicts.json()["items"][0]["candidates"]) >= 2
