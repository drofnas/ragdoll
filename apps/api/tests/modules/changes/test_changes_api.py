from __future__ import annotations

from io import BytesIO

import pytest

from tests.modules._phase10_helpers import auth_headers, build_processing_runtime, register_and_login
from tests.support.document_processing import drain_test_document_jobs


@pytest.fixture
def processing_runtime(api_client):
    runtime = build_processing_runtime(api_client)
    try:
        yield runtime
    finally:
        api_client.app.dependency_overrides.clear()


def test_changes_capture_processing_and_read_state(api_client, processing_runtime):
    storage, queue, embedding_service, entity_extraction_service = processing_runtime
    token = register_and_login(api_client, email="owner@example.com")

    upload = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token),
        files={"file": ("alpha.txt", BytesIO(b"Atlas rollout information"), "text/plain")},
    )
    assert upload.status_code == 201, upload.text

    processed = drain_test_document_jobs(
        queue=queue,
        storage=storage,
        embedding_service=embedding_service,
        entity_extraction_service=entity_extraction_service,
    )
    assert processed == 1

    listing = api_client.get("/api/v1/changes", headers=auth_headers(token))
    assert listing.status_code == 200, listing.text
    assert any(item["event_type"] == "document_processed" for item in listing.json()["items"])

    change_id = listing.json()["items"][0]["id"]
    detail = api_client.get(f"/api/v1/changes/{change_id}", headers=auth_headers(token))
    assert detail.status_code == 200, detail.text

    marked = api_client.post(f"/api/v1/changes/{change_id}/read", headers=auth_headers(token))
    assert marked.status_code == 200, marked.text

    reread = api_client.get(f"/api/v1/changes/{change_id}", headers=auth_headers(token))
    assert reread.status_code == 200, reread.text
    assert reread.json()["is_read"] is True
