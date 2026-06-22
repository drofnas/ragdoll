from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
CONTRACT_SCRIPT = REPO_ROOT / "packages" / "tooling" / "scripts" / "generate_contracts.py"


def test_openapi_export_includes_retrieval_read_contracts(configured_database, tmp_path):
    openapi_output = tmp_path / "ragdoll.openapi.json"
    typescript_manifest = tmp_path / "typescript" / "manifest.json"

    completed = subprocess.run(
        [
            "python3",
            str(CONTRACT_SCRIPT),
            "--openapi-output",
            str(openapi_output),
            "--typescript-manifest",
            str(typescript_manifest),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(openapi_output.read_text(encoding="utf-8"))

    assert "/api/v1/search" in payload["paths"]
    assert "/api/v1/entities" in payload["paths"]
    assert "/api/v1/entities/{entity_id}" in payload["paths"]
    assert "/api/v1/knowledge-graph/entities/{entity_id}/subgraph" in payload["paths"]
    assert "/api/v1/knowledge-graph/documents/{document_id}" in payload["paths"]

    schemas = payload["components"]["schemas"]
    assert "SearchResponse" in schemas
    assert "SearchMode" in schemas
    assert "EntityDetailResponse" in schemas
    assert "GraphResponse" in schemas
