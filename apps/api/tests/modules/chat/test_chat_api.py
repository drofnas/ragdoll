from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from ragdoll.api.shared_schemas import Citation, SourceTier
from ragdoll.modules.chat.application import commands as chat_commands
from ragdoll.modules.chat.application.evidence import ChatEvidenceItem
from ragdoll.modules.chat.application.service import compose_deterministic_evidence_answer, compose_fallback_answer
from ragdoll.modules.search.api.schemas import SearchEntitySummary, SearchMode, SearchResult, SearchResultDocument
from ragdoll.platform.db.models import TrackedField, TrackedFieldValue, User

from tests.modules._phase10_helpers import auth_headers, default_space, register_and_login, seed_retrieval_document


class FakeChatCompletionService:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.messages = []

    def generate(self, messages):
        self.messages = messages
        return self.answer


class FailingChatCompletionService:
    def generate(self, messages):
        raise TimeoutError("chat model unavailable")


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
        start_line=4,
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
    assert payload["assistant_message"]["evidence"]
    assert payload["assistant_message"]["citations"][0]["line_number"] == 4
    assert "Atlas" in payload["assistant_message"]["content"]
    assert payload["session"]["title"].startswith("Tell me about Atlas")


def test_chat_synthesis_success_persists_compact_evidence_audit(api_client, db_session, monkeypatch):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    seed_retrieval_document(
        db_session,
        space=default_space(db_session, owner),
        uploader=owner,
        title="atlas.txt",
        text="Atlas uses a Go backend and a Svelte frontend.",
        entity_specs=[("Atlas", "project")],
        start_line=12,
    )
    fake_service = FakeChatCompletionService("Atlas uses Go for backend work and Svelte for frontend work. [E1]")
    monkeypatch.setattr(chat_commands, "get_chat_completion_service", lambda: fake_service)

    created = api_client.post("/api/v1/chat/sessions", headers=auth_headers(token))
    session_id = created.json()["id"]
    message = api_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "What is the Atlas stack?"},
    )

    assert message.status_code == 200, message.text
    assistant_message = message.json()["assistant_message"]
    assert assistant_message["degraded"] is False
    assert assistant_message["content"] == fake_service.answer
    assert assistant_message["citations"][0]["line_number"] == 12
    assert assistant_message["evidence"][0]["id"] == "E1"
    assert assistant_message["evidence"][0]["source_type"] == "document_chunk"
    assert message.json()["session"]["messages"][-1]["evidence"][0]["id"] == "E1"
    prompt = fake_service.messages[-1].content
    assert "answerability=" in prompt
    assert "source=document_chunk" in prompt


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


def test_document_scoped_chat_uses_technology_stack_chunk_for_stack_questions(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    space = default_space(db_session, owner)
    stack_chunk = (
        "### Technology Stack\n\n"
        "| Component | Technology | Justification |\n"
        "| **Backend Service** | Go 1.21+ | Fast file I/O and single binary deployment |\n"
        "| **AI Service** | Python 3.10+ | Best ML library ecosystem |\n"
        "| **Frontend** | Svelte + SvelteKit | Reactive, small bundle size |\n"
        "| **Desktop App** | Electron | Cross-platform desktop wrapper |\n"
    )
    install_chunk = (
        "### Platform-Specific Deployment\n\n"
        "Installation Locations: Application: C:\\Program Files\\FilegoGallery\\. "
        "Services: C:\\Program Files\\FilegoGallery\\services\\. "
        "User Data: C:\\Users\\{username}\\AppData\\Roaming\\FilegoGallery\\. "
        "Cache: C:\\Users\\{username}\\AppData\\Local\\FilegoGallery\\cache\\. "
        "FilegoGallery services stop and remove FilegoGallery files automatically."
    )
    filego_document = seed_retrieval_document(
        db_session,
        space=space,
        uploader=owner,
        title="filegogallery-prd.md",
        text=f"{stack_chunk}\n\n{install_chunk}",
        file_type="md",
        mime_type="text/markdown",
        entity_specs=[("FilegoGallery", "product")],
        chunks=[(stack_chunk, 129), (install_chunk, 1257)],
    )

    created = api_client.post(
        f"/api/v1/chat/sessions?space_id={space.id}&document_id={filego_document.id}",
        headers=auth_headers(token),
    )
    assert created.status_code == 200, created.text
    session_id = created.json()["id"]

    message = api_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "Does the FileGo Gallery have any details about what tech stack, programming languages, etc?"},
    )

    assert message.status_code == 200, message.text
    assistant_message = message.json()["assistant_message"]
    assert "technology stack" in assistant_message["content"].lower()
    assert "go 1.21+" in assistant_message["content"].lower()
    assert "python 3.10+" in assistant_message["content"].lower()
    assert "c:\\program files" not in assistant_message["content"].lower()
    assert [citation["line_number"] for citation in assistant_message["citations"]] == [129]


def test_document_scoped_chat_degraded_fallback_extracts_filego_technology_stack(
    api_client,
    db_session,
    monkeypatch,
):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    space = default_space(db_session, owner)
    architecture_chunk = (
        "### Architecture Overview\n\n"
        "│              FileGoGallery Desktop Application              │\n"
        "│  └─ Svelte Frontend (Web UI) ─ Connects to: http://localhost:8080 │\n"
        "│          Go Backend Service (filegogallery-fs)              │\n"
        "│  └─ Tagging Service Client (calls Python service)          │\n"
    )
    stack_chunk = (
        "### Technology Stack\n\n"
        "| Component | Technology | Justification |\n"
        "|-----------|------------|---------------|\n"
        "| **Backend Service** | Go 1.21+ | Fast file I/O, excellent concurrency, single binary deployment |\n"
        "| **Backend Framework** | Fiber or Echo | High-performance HTTP routing, WebSocket support |\n"
        "| **Database** | SQLite 3 | Zero-config, embedded, 10k+ images with sub-second queries |\n"
        "| **AI Service** | Python 3.10+ | Best ML library ecosystem |\n"
        "| **AI Framework** | FastAPI + Uvicorn | Async HTTP, auto-generated docs, fast |\n"
        "| **Frontend** | Svelte + SvelteKit | Reactive, small bundle size, excellent DX |\n"
        "| **Frontend Build** | Vite | Fast HMR, optimized production builds |\n"
        "| **Desktop App** | Electron | Cross-platform desktop wrapper, native OS integration |\n"
        "| **Packaging** | electron-builder | Multi-platform installers with service installation |\n"
    )
    websocket_chunk = (
        "### WebSocket Events\n\n"
        "```json\n"
        "{ \"type\": \"image_updated\", \"timestamp\": \"2025-11-08T15:30:00Z\", "
        "\"data\": { \"id\": \"abc123\" } }\n"
        "```\n"
    )
    electron_chunk = (
        "### Electron IPC\n\n"
        "```javascript\n"
        "ipcMain.on('start-drag', (event, { filepath, thumbnailPath }) => {\n"
        "  event.sender.startDrag({ file: filepath, icon: thumbnailPath });\n"
        "});\n"
        "```\n"
    )
    deployment_chunk = (
        "### Platform-Specific Deployment\n\n"
        "Installation Locations: Services: C:\\Program Files\\FileGoGallery\\services\\. "
        "User Data: C:\\Users\\{username}\\AppData\\Roaming\\FileGoGallery\\. "
        "Binds: [ ${userDataPath}/cache:/app/cache, ${photoLibraryPath}:/mnt/images:ro ]. "
        "const containerInfo = await docker.getContainer(backend.Id);\n"
    )
    filego_document = seed_retrieval_document(
        db_session,
        space=space,
        uploader=owner,
        title="filegogallery-prd.md",
        text="\n\n".join([architecture_chunk, stack_chunk, websocket_chunk, electron_chunk, deployment_chunk]),
        file_type="md",
        mime_type="text/markdown",
        entity_specs=[("FileGoGallery", "product")],
        chunks=[
            (architecture_chunk, 62),
            (stack_chunk, 124),
            (websocket_chunk, 920),
            (electron_chunk, 1130),
            (deployment_chunk, 1257),
        ],
    )
    monkeypatch.setattr(chat_commands, "get_chat_completion_service", lambda: FailingChatCompletionService())

    created = api_client.post(
        f"/api/v1/chat/sessions?space_id={space.id}&document_id={filego_document.id}",
        headers=auth_headers(token),
    )
    assert created.status_code == 200, created.text
    session_id = created.json()["id"]

    message = api_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "Return the Tech stack in a bulleted list for the FileGo Gallery"},
    )

    assert message.status_code == 200, message.text
    assistant_message = message.json()["assistant_message"]
    answer_text = assistant_message["content"].lower()
    assert assistant_message["degraded"] is True
    assert "backend service: go 1.21+" in answer_text
    assert "ai service: python 3.10+" in answer_text
    assert "database: sqlite 3" in answer_text
    assert "ai framework: fastapi + uvicorn" in answer_text
    assert "frontend: svelte + sveltekit" in answer_text
    assert "frontend build: vite" in answer_text
    assert "desktop app: electron" in answer_text
    assert "packaging: electron-builder" in answer_text
    assert "localhost:8080" not in answer_text
    assert "c:\\program files" not in answer_text
    assert "image_updated" not in answer_text
    assert "ipcmain" not in answer_text
    assert "docker.getcontainer" not in answer_text
    assert "│" not in assistant_message["content"]
    assert [citation["line_number"] for citation in assistant_message["citations"]] == [124]
    assert assistant_message["evidence"][0]["source_type"] == "document_chunk"
    assert "Technology Stack" in assistant_message["evidence"][0]["text"]


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


def test_deterministic_technology_stack_fallback_refuses_noisy_evidence():
    noisy_item = ChatEvidenceItem(
        id="E1",
        source_type="document_chunk",
        source_tier=SourceTier.DOCUMENT,
        text=(
            "Frontend (Web UI) connects to http://localhost:8080. "
            "{ \"type\": \"image_updated\", \"timestamp\": \"2025-11-08T15:30:00Z\" } "
            "Services: C:\\Program Files\\FileGoGallery\\services\\."
        ),
        citations=[],
        score=-20.0,
        title="filegogallery-prd.md",
        answer_intent="technology_stack",
        answerability=-50.0,
    )

    answer_text = compose_deterministic_evidence_answer(
        query_text="Return the Tech stack in a bulleted list for the FileGo Gallery",
        evidence_items=[noisy_item],
    )

    assert "could not produce a reliable answer" in answer_text.lower()
    assert "localhost:8080" not in answer_text.lower()
    assert "image_updated" not in answer_text.lower()
    assert "c:\\program files" not in answer_text.lower()


def test_deterministic_technology_stack_fallback_parses_split_table_rows():
    split_table_item = ChatEvidenceItem(
        id="E1",
        source_type="document_chunk",
        source_tier=SourceTier.DOCUMENT,
        text=(
            "I/O, excellent concurrency, single binary deployment |\n"
            "| **Backend Framework** | Fiber or Echo | High-performance HTTP routing |\n"
            "| **Database** | SQLite 3 | Zero-config embedded database |\n"
            "| **AI Service** | Python 3.10+ | Best ML ecosystem |\n"
        ),
        citations=[],
        score=85.0,
        title="filegogallery-prd.md",
        answer_intent="technology_stack",
        answerability=85.0,
    )

    answer_text = compose_deterministic_evidence_answer(
        query_text="Return the Tech stack in a bulleted list for the FileGo Gallery",
        evidence_items=[split_table_item],
    )

    assert "- Backend Framework: Fiber or Echo [E1]" in answer_text
    assert "- Database: SQLite 3 [E1]" in answer_text
    assert "- AI Service: Python 3.10+ [E1]" in answer_text


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
    assistant_message = message.json()["assistant_message"]
    assert "Atlas is paused" in assistant_message["content"]
    assert "active" not in assistant_message["content"].lower()
    assert assistant_message["evidence"][0]["source_type"] == "correction"


def test_chat_answer_includes_current_tracked_state_as_pinned_evidence(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    space = default_space(db_session, owner)
    field = TrackedField(
        space_id=space.id,
        owner_user_id=owner.id,
        key="release_status",
        label="Release status",
        prompt="What is the current release status?",
        is_active=True,
    )
    db_session.add(field)
    db_session.flush()
    db_session.add(
        TrackedFieldValue(
            tracked_field_id=field.id,
            space_id=space.id,
            source_tier=SourceTier.VERIFIED.value,
            value_text="Atlas is paused for security review.",
            citations=[],
            is_current=True,
        )
    )
    db_session.commit()

    session_response = api_client.post("/api/v1/chat/sessions", headers=auth_headers(token))
    session_id = session_response.json()["id"]
    message = api_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "What is the release status?"},
    )

    assert message.status_code == 200, message.text
    assistant_message = message.json()["assistant_message"]
    assert "Release status: Atlas is paused for security review" in assistant_message["content"]
    assert any(item["source_type"] == "tracked_state" for item in assistant_message["evidence"])


def test_document_scoped_chat_includes_graph_relationship_evidence(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    space = default_space(db_session, owner)
    document = seed_retrieval_document(
        db_session,
        space=space,
        uploader=owner,
        title="atlas-architecture.md",
        text="Atlas connects the Go API to the Svelte client.",
        entity_specs=[("Go API", "component"), ("Svelte Client", "component")],
    )

    session_response = api_client.post(
        f"/api/v1/chat/sessions?space_id={space.id}&document_id={document.id}",
        headers=auth_headers(token),
    )
    session_id = session_response.json()["id"]
    message = api_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "How are the architecture components related?"},
    )

    assert message.status_code == 200, message.text
    evidence = message.json()["assistant_message"]["evidence"]
    assert any(item["source_type"] == "document_chunk" for item in evidence)
    assert any(item["source_type"] == "graph_relationship" for item in evidence)


def test_chat_synthesis_prompt_includes_recent_history(api_client, db_session, monkeypatch):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    seed_retrieval_document(
        db_session,
        space=default_space(db_session, owner),
        uploader=owner,
        title="atlas.txt",
        text="Atlas uses Svelte for its frontend.",
        entity_specs=[("Atlas", "project")],
    )
    session_response = api_client.post("/api/v1/chat/sessions", headers=auth_headers(token))
    session_id = session_response.json()["id"]
    first = api_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "Tell me about Atlas"},
    )
    assert first.status_code == 200, first.text

    fake_service = FakeChatCompletionService("It uses Svelte for the frontend. [E1]")
    monkeypatch.setattr(chat_commands, "get_chat_completion_service", lambda: fake_service)
    second = api_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers(token),
        json={"content": "What about the frontend?"},
    )

    assert second.status_code == 200, second.text
    prompt = fake_service.messages[-1].content
    assert "Recent chat history:" in prompt
    assert "Tell me about Atlas" in prompt
    assert "What about the frontend?" in prompt
