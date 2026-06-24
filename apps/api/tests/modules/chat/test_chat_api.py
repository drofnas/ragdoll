from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from ragdoll.api.shared_schemas import Citation, SourceTier
from ragdoll.modules.chat.application.service import compose_fallback_answer
from ragdoll.modules.search.api.schemas import SearchEntitySummary, SearchMode, SearchResult, SearchResultDocument
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


def test_document_scoped_chat_only_cites_the_selected_document(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    space = default_space(db_session, owner)
    filego_document = seed_retrieval_document(
        db_session,
        space=space,
        uploader=owner,
        title="filegogallery-prd.md",
        text="FilegoGallery is an AI-powered desktop gallery application for large image libraries.",
        entity_specs=[("FilegoGallery", "product")],
    )
    seed_retrieval_document(
        db_session,
        space=space,
        uploader=owner,
        title="iam-plan.md",
        text="API Access Control policy for enterprise identity governance.",
        entity_specs=[("API", "topic"), ("Access Control", "topic")],
    )

    created = api_client.post(
        f"/api/v1/chat/sessions?space_id={space.id}&document_id={filego_document.id}",
        headers=auth_headers(token),
    )
    assert created.status_code == 200, created.text
    assert created.json()["document_id"] == str(filego_document.id)
    session_id = created.json()["id"]

    message = api_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "Tell me about the FileGo application"},
    )
    assert message.status_code == 200, message.text
    payload = message.json()
    citations = payload["assistant_message"]["citations"]
    assert citations
    assert all(item["document_id"] == str(filego_document.id) for item in citations)
    assert "filegogallery is an ai-powered desktop gallery application" in payload["assistant_message"]["content"].lower()
    assert "current evidence for" not in payload["assistant_message"]["content"].lower()
    assert "filegogallery-prd.md:" not in payload["assistant_message"]["content"].lower()


def test_space_wide_chat_prefers_document_evidence_for_specific_summary_queries(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    space = default_space(db_session, owner)
    filego_document = seed_retrieval_document(
        db_session,
        space=space,
        uploader=owner,
        title="filegogallery-prd.md",
        text="FilegoGallery is an AI-powered desktop gallery application built for local image libraries.",
        entity_specs=[("FilegoGallery", "product")],
    )
    seed_retrieval_document(
        db_session,
        space=space,
        uploader=owner,
        title="security-notes.md",
        text="API Access Control and lifecycle governance requirements.",
        entity_specs=[("API", "topic"), ("Access Control", "topic")],
    )

    created = api_client.post(f"/api/v1/chat/sessions?space_id={space.id}", headers=auth_headers(token))
    assert created.status_code == 200, created.text
    session_id = created.json()["id"]

    message = api_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "Tell me about the FileGo application"},
    )
    assert message.status_code == 200, message.text
    payload = message.json()
    assert payload["assistant_message"]["citations"][0]["document_id"] == str(filego_document.id)
    assert "api | access control" not in payload["assistant_message"]["content"].lower()
    assert "current evidence for" not in payload["assistant_message"]["content"].lower()
    assert "filegogallery-prd.md:" not in payload["assistant_message"]["content"].lower()


def test_fallback_answer_prefers_document_summaries_over_entity_labels_when_available():
    document_id = UUID("55555555-5555-5555-5555-555555555555")
    space_id = UUID("33333333-3333-3333-3333-333333333333")
    created_at = datetime(2026, 6, 23, 20, 17, 29, tzinfo=timezone.utc)
    retrieval_results = [
        SearchResult(
            result_id="chunk-1",
            result_kind="document_chunk",
            score=4.2,
            matched_modes=[SearchMode.BOOLEAN, SearchMode.VECTOR],
            document=SearchResultDocument(
                id=document_id,
                space_id=space_id,
                title="filegogallery-prd.md",
                file_type="md",
                created_at=created_at,
            ),
            preview_text="FilegoGallery is an AI-powered desktop gallery app.",
            entity=None,
            citations=[
                Citation(
                    document_id=document_id,
                    chunk_id="chunk-1",
                    title="filegogallery-prd.md",
                    locator="chunk:1",
                    source_tier=SourceTier.DOCUMENT,
                )
            ],
        ),
        SearchResult(
            result_id="entity-1",
            result_kind="entity",
            score=4.1,
            matched_modes=[SearchMode.GRAPH],
            document=None,
            preview_text="API",
            entity=SearchEntitySummary(
                id=UUID("11111111-1111-1111-1111-111111111111"),
                entity_type="topic",
                display_name="API",
                normalized_name="api",
                mention_count=8,
            ),
            citations=[],
        ),
    ]

    answer_text, _, _ = compose_fallback_answer(
        query_text="Tell me about the FileGo application",
        retrieval_results=retrieval_results,
        verified_corrections=[],
        document_id=document_id,
    )

    assert "filegogallery is an ai-powered desktop gallery app." in answer_text.lower()
    assert "current evidence for" not in answer_text.lower()
    assert "filegogallery-prd.md:" not in answer_text.lower()
    assert "api |" not in answer_text.lower()


def test_fallback_answer_uses_document_intro_for_summary_questions():
    document_id = UUID("55555555-5555-5555-5555-555555555555")
    space_id = UUID("33333333-3333-3333-3333-333333333333")
    created_at = datetime(2026, 6, 23, 20, 17, 29, tzinfo=timezone.utc)
    retrieval_results = [
        SearchResult(
            result_id="chunk-23",
            result_kind="document_chunk",
            score=5.1,
            matched_modes=[SearchMode.BOOLEAN],
            document=SearchResultDocument(
                id=document_id,
                space_id=space_id,
                title="filegogallery-prd.md",
                file_type="md",
                created_at=created_at,
            ),
            preview_text=(
                "Services: C:\\Program Files\\FilegoGallery\\services\\ - User Data: "
                "C:\\Users\\{username}\\AppData\\Roaming\\FilegoGallery\\"
            ),
            entity=None,
            citations=[
                Citation(
                    document_id=document_id,
                    chunk_id="chunk-23",
                    title="filegogallery-prd.md",
                    locator="chunk:23",
                    source_tier=SourceTier.DOCUMENT,
                )
            ],
        )
    ]

    answer_text, _, _ = compose_fallback_answer(
        query_text="What is the Filego Gallery?",
        retrieval_results=retrieval_results,
        verified_corrections=[],
        document_id=document_id,
        document_context={
            document_id: (
                "# Product Requirements Document\n\n"
                "## Executive Summary\n\n"
                "FilegoGallery is a high-performance, AI-powered desktop image gallery application "
                "designed to handle large-scale image libraries stored on local filesystems or network-attached storage.\n\n"
                "## Installation\n\n"
                "Services: C:\\Program Files\\FilegoGallery\\services\\"
            )
        },
    )

    assert "ai-powered desktop image gallery application" in answer_text.lower()
    assert "c:\\program files" not in answer_text.lower()
    assert "current evidence for" not in answer_text.lower()
    assert "filegogallery-prd.md:" not in answer_text.lower()


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
