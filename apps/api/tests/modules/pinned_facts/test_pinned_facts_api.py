from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from ragdoll.api.shared_schemas import Citation
from ragdoll.modules.search.api.schemas import SearchEntitySummary, SearchMode, SearchResult, SearchResultDocument
from ragdoll.platform.db.models import User

from tests.modules._phase10_helpers import auth_headers, default_space, register_and_login


def _search_result(*, space_id, document_id, value: str, quote: str) -> SearchResult:
    return SearchResult(
        result_id=str(uuid4()),
        result_kind="entity",
        score=0.97,
        matched_modes=[SearchMode.COMBINED],
        document=SearchResultDocument(
            id=document_id,
            space_id=space_id,
            title=f"{value}.txt",
            file_type="txt",
            created_at=datetime.now(timezone.utc),
        ),
        preview_text=quote,
        entity=SearchEntitySummary(
            id=uuid4(),
            entity_type="project",
            display_name=value,
            normalized_name=value.lower(),
            mention_count=1,
        ),
        citations=[
            Citation(
                document_id=document_id,
                locator="chunk:1",
                chunk_id="chunk-1",
                title=f"{value}.txt",
                source_tier="document",
            )
        ],
    )


def _create_fact(
    api_client,
    token: str,
    *,
    title: str = "Focus Project",
    description: str = "What is the focus project?",
    value_kind: str = "text",
    value_text: str | None = "Atlas",
    value_json: dict[str, object] | None = None,
    evidence: list[dict[str, object]] | None = None,
):
    return api_client.post(
        "/api/v1/pinned-facts",
        headers=auth_headers(token),
        json={
            "key": "focus_project",
            "title": title,
            "description": description,
            "value_kind": value_kind,
            "value_text": value_text,
            "value_json": value_json,
            "confidence": 0.95,
            "evidence": evidence
            or [
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


def test_manual_create_supports_text_output_and_stores_all_evidence(api_client):
    token = register_and_login(api_client, email="owner@example.com")
    response = _create_fact(
        api_client,
        token,
        evidence=[
            {"quote": "Atlas is the current focus project.", "citations": [], "source_chunk_ids": []},
            {"quote": "Atlas remains the active initiative.", "citations": [], "source_chunk_ids": []},
        ],
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["value_kind"] == "text"
    assert payload["value_text"] == "Atlas"
    assert len(payload["evidence"]) == 2

    history = api_client.get(f"/api/v1/pinned-facts/{payload['id']}/history", headers=auth_headers(token))
    assert history.status_code == 200, history.text
    assert len(history.json()["items"][0]["new_evidence"]) == 2


def test_manual_create_supports_json_output(api_client):
    token = register_and_login(api_client, email="owner@example.com")
    response = _create_fact(
        api_client,
        token,
        title="Theme Tokens",
        description="What are the theme tokens?",
        value_kind="json",
        value_text=None,
        value_json={"primary": "#2563eb", "accent": "#0f172a"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["value_kind"] == "json"
    assert payload["value_json"] == {"primary": "#2563eb", "accent": "#0f172a"}


def test_rerun_detects_pending_update_when_answer_changes(api_client, db_session, monkeypatch):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    space = default_space(db_session, owner)
    document_id = uuid4()
    created = api_client.post(
        f"/api/v1/pinned-facts?space_id={space.id}",
        headers=auth_headers(token),
        json={
            "key": "focus_project",
            "title": "Focus Project",
            "description": "What is the focus project?",
            "value_kind": "text",
            "value_text": "Atlas",
            "confidence": 0.95,
            "evidence": [{"quote": "Atlas is the current focus project.", "citations": [], "source_chunk_ids": []}],
        },
    )
    fact_id = created.json()["id"]

    monkeypatch.setattr(
        "ragdoll.modules.pinned_facts.application.service.retrieve_search_results",
        lambda *args, **kwargs: [
            _search_result(space_id=space.id, document_id=document_id, value="Northstar", quote="Northstar is the focus project.")
        ],
    )

    rechecked = api_client.post(
        f"/api/v1/pinned-facts/{fact_id}/recheck?space_id={space.id}",
        headers=auth_headers(token),
    )
    assert rechecked.status_code == 200, rechecked.text
    assert rechecked.json()["status"] == "pending_update"
    assert rechecked.json()["value_text"] == "Atlas"

    candidates = api_client.get(
        f"/api/v1/pinned-facts/{fact_id}/candidates?space_id={space.id}",
        headers=auth_headers(token),
    )
    assert candidates.status_code == 200, candidates.text
    assert candidates.json()["items"][0]["proposed_value_text"] == "Northstar"
    assert candidates.json()["items"][0]["status"] == "pending"


def test_rerun_detects_evidence_only_update(api_client, db_session, monkeypatch):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    space = default_space(db_session, owner)
    document_id = uuid4()
    created = api_client.post(
        f"/api/v1/pinned-facts?space_id={space.id}",
        headers=auth_headers(token),
        json={
            "key": "focus_project",
            "title": "Focus Project",
            "description": "What is the focus project?",
            "value_kind": "text",
            "value_text": "Atlas",
            "confidence": 0.95,
            "evidence": [{"quote": "Atlas was referenced in the kickoff doc.", "citations": [], "source_chunk_ids": []}],
        },
    )
    fact_id = created.json()["id"]

    monkeypatch.setattr(
        "ragdoll.modules.pinned_facts.application.service.retrieve_search_results",
        lambda *args, **kwargs: [
            _search_result(space_id=space.id, document_id=document_id, value="Atlas", quote="Atlas is still the focus project.")
        ],
    )

    rechecked = api_client.post(
        f"/api/v1/pinned-facts/{fact_id}/recheck?space_id={space.id}",
        headers=auth_headers(token),
    )
    assert rechecked.status_code == 200, rechecked.text
    assert rechecked.json()["status"] == "pending_update"

    candidates = api_client.get(
        f"/api/v1/pinned-facts/{fact_id}/candidates?space_id={space.id}",
        headers=auth_headers(token),
    )
    assert candidates.status_code == 200, candidates.text
    assert candidates.json()["items"][0]["change_type"] == "evidence_update"
    assert candidates.json()["items"][0]["proposed_value_text"] == "Atlas"


def test_accept_update_writes_history(api_client, db_session, monkeypatch):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    space = default_space(db_session, owner)
    document_id = uuid4()
    created = api_client.post(
        f"/api/v1/pinned-facts?space_id={space.id}",
        headers=auth_headers(token),
        json={
            "key": "focus_project",
            "title": "Focus Project",
            "description": "What is the focus project?",
            "value_kind": "text",
            "value_text": "Atlas",
            "confidence": 0.95,
            "evidence": [{"quote": "Atlas is the current focus project.", "citations": [], "source_chunk_ids": []}],
        },
    )
    fact_id = created.json()["id"]
    monkeypatch.setattr(
        "ragdoll.modules.pinned_facts.application.service.retrieve_search_results",
        lambda *args, **kwargs: [
            _search_result(space_id=space.id, document_id=document_id, value="Northstar", quote="Northstar is the focus project.")
        ],
    )
    api_client.post(f"/api/v1/pinned-facts/{fact_id}/recheck?space_id={space.id}", headers=auth_headers(token))
    candidates = api_client.get(
        f"/api/v1/pinned-facts/{fact_id}/candidates?space_id={space.id}",
        headers=auth_headers(token),
    ).json()["items"]

    accepted = api_client.post(
        f"/api/v1/pinned-facts/candidates/{candidates[0]['id']}/accept?space_id={space.id}",
        headers=auth_headers(token),
        json={"review_notes": "Verified with the latest source."},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["value_text"] == "Northstar"

    history = api_client.get(f"/api/v1/pinned-facts/{fact_id}/history", headers=auth_headers(token))
    assert history.status_code == 200, history.text
    assert history.json()["items"][0]["reason"] == "candidate_accepted"
    assert history.json()["items"][0]["update_note"] == "Verified with the latest source."


def test_accept_update_clears_other_pending_candidates(api_client, db_session, monkeypatch):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    space = default_space(db_session, owner)
    document_id = uuid4()
    created = api_client.post(
        f"/api/v1/pinned-facts?space_id={space.id}",
        headers=auth_headers(token),
        json={
            "key": "focus_project",
            "title": "Focus Project",
            "description": "What is the focus project?",
            "value_kind": "text",
            "value_text": "Atlas",
            "confidence": 0.95,
            "evidence": [{"quote": "Atlas is the current focus project.", "citations": [], "source_chunk_ids": []}],
        },
    )
    fact_id = created.json()["id"]
    monkeypatch.setattr(
        "ragdoll.modules.pinned_facts.application.service.retrieve_search_results",
        lambda *args, **kwargs: [
            _search_result(space_id=space.id, document_id=document_id, value="Northstar", quote="Northstar is the focus project."),
            _search_result(space_id=space.id, document_id=document_id, value="Compass", quote="Compass is the focus project."),
        ],
    )
    api_client.post(f"/api/v1/pinned-facts/{fact_id}/recheck?space_id={space.id}", headers=auth_headers(token))
    candidates = api_client.get(
        f"/api/v1/pinned-facts/{fact_id}/candidates?space_id={space.id}",
        headers=auth_headers(token),
    ).json()["items"]
    assert len(candidates) == 2

    accepted = api_client.post(
        f"/api/v1/pinned-facts/candidates/{candidates[0]['id']}/accept?space_id={space.id}",
        headers=auth_headers(token),
        json={"review_notes": "Use this value."},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "active"
    assert accepted.json()["pending_candidate_count"] == 0

    reviewed = api_client.get(
        f"/api/v1/pinned-facts/{fact_id}/candidates?space_id={space.id}",
        headers=auth_headers(token),
    )
    assert reviewed.status_code == 200, reviewed.text
    statuses = {item["proposed_value_text"]: item["status"] for item in reviewed.json()["items"]}
    assert list(statuses.values()).count("accepted") == 1
    assert list(statuses.values()).count("rejected") == 1


def test_reject_update_preserves_current_value(api_client, db_session, monkeypatch):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    space = default_space(db_session, owner)
    document_id = uuid4()
    created = api_client.post(
        f"/api/v1/pinned-facts?space_id={space.id}",
        headers=auth_headers(token),
        json={
            "key": "focus_project",
            "title": "Focus Project",
            "description": "What is the focus project?",
            "value_kind": "text",
            "value_text": "Atlas",
            "confidence": 0.95,
            "evidence": [{"quote": "Atlas is the current focus project.", "citations": [], "source_chunk_ids": []}],
        },
    )
    fact_id = created.json()["id"]
    monkeypatch.setattr(
        "ragdoll.modules.pinned_facts.application.service.retrieve_search_results",
        lambda *args, **kwargs: [
            _search_result(space_id=space.id, document_id=document_id, value="Northstar", quote="Northstar is the focus project.")
        ],
    )
    api_client.post(f"/api/v1/pinned-facts/{fact_id}/recheck?space_id={space.id}", headers=auth_headers(token))
    candidates = api_client.get(
        f"/api/v1/pinned-facts/{fact_id}/candidates?space_id={space.id}",
        headers=auth_headers(token),
    ).json()["items"]

    rejected = api_client.post(
        f"/api/v1/pinned-facts/candidates/{candidates[0]['id']}/reject?space_id={space.id}",
        headers=auth_headers(token),
        json={"review_notes": "Keep Atlas until launch planning completes."},
    )
    assert rejected.status_code == 200, rejected.text

    detail = api_client.get(f"/api/v1/pinned-facts/{fact_id}?space_id={space.id}", headers=auth_headers(token))
    assert detail.status_code == 200, detail.text
    assert detail.json()["value_text"] == "Atlas"
    assert detail.json()["status"] == "active"


def test_manual_edit_writes_history_updated_by_and_optional_update_note(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    created = _create_fact(api_client, token)
    fact_id = created.json()["id"]

    updated = api_client.patch(
        f"/api/v1/pinned-facts/{fact_id}",
        headers=auth_headers(token),
        json={
            "value_kind": "text",
            "value_text": "Northstar",
            "update_note": "Manual correction after product review.",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["value_text"] == "Northstar"
    assert updated.json()["updated_by"]["id"] == str(owner.id)

    history = api_client.get(f"/api/v1/pinned-facts/{fact_id}/history", headers=auth_headers(token))
    assert history.status_code == 200, history.text
    assert history.json()["items"][0]["reason"] == "manual_edit"
    assert history.json()["items"][0]["update_note"] == "Manual correction after product review."


def test_full_rerun_creates_pending_update_only_when_changes_exist(api_client, db_session, monkeypatch):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    space = default_space(db_session, owner)
    document_id = uuid4()
    quote = "Atlas is the current focus project."
    created = api_client.post(
        f"/api/v1/pinned-facts?space_id={space.id}",
        headers=auth_headers(token),
        json={
            "key": "focus_project",
            "title": "Focus Project",
            "description": "What is the focus project?",
            "value_kind": "text",
            "value_text": "Atlas",
            "confidence": 0.95,
            "evidence": [
                {
                    "quote": quote,
                    "citations": [
                        {
                            "document_id": str(document_id),
                            "locator": "chunk:1",
                            "chunk_id": "chunk-1",
                            "title": "Atlas.txt",
                            "source_tier": "document",
                        }
                    ],
                    "source_chunk_ids": ["chunk-1"],
                }
            ],
        },
    )
    fact_id = created.json()["id"]

    monkeypatch.setattr(
        "ragdoll.modules.pinned_facts.application.service.retrieve_search_results",
        lambda *args, **kwargs: [
            _search_result(space_id=space.id, document_id=document_id, value="Atlas", quote=quote)
        ],
    )
    rechecked = api_client.post(
        f"/api/v1/pinned-facts/{fact_id}/recheck?space_id={space.id}",
        headers=auth_headers(token),
    )
    assert rechecked.status_code == 200, rechecked.text
    assert rechecked.json()["status"] == "active"

    candidates = api_client.get(
        f"/api/v1/pinned-facts/{fact_id}/candidates?space_id={space.id}",
        headers=auth_headers(token),
    )
    assert candidates.status_code == 200, candidates.text
    assert candidates.json()["items"] == []


def test_missing_evidence_warning(api_client, db_session, monkeypatch):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    space = default_space(db_session, owner)
    created = api_client.post(
        f"/api/v1/pinned-facts?space_id={space.id}",
        headers=auth_headers(token),
        json={
            "key": "focus_project",
            "title": "Focus Project",
            "description": "What is the focus project?",
            "value_kind": "text",
            "value_text": "Atlas",
            "confidence": 0.95,
            "evidence": [{"quote": "Atlas is the current focus project.", "citations": [], "source_chunk_ids": []}],
        },
    )
    fact_id = created.json()["id"]

    monkeypatch.setattr(
        "ragdoll.modules.pinned_facts.application.service.retrieve_search_results",
        lambda *args, **kwargs: [],
    )

    rechecked = api_client.post(
        f"/api/v1/pinned-facts/{fact_id}/recheck?space_id={space.id}",
        headers=auth_headers(token),
    )
    assert rechecked.status_code == 200, rechecked.text
    assert rechecked.json()["status"] == "missing_evidence"
    assert rechecked.json()["value_text"] == "Atlas"
