from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
CONTRACT_SCRIPT = REPO_ROOT / "packages" / "tooling" / "scripts" / "generate_contracts.py"


def test_openapi_export_includes_ingestion_contracts(configured_database, tmp_path):
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

    assert "/api/v1/ingestion/uploads" in payload["paths"]
    assert "/api/v1/ingestion/documents/{document_id}/status" in payload["paths"]
    assert "/api/v1/ingestion/documents/status/batch" in payload["paths"]
    assert "/api/v1/ingestion/documents/{document_id}/reprocess" in payload["paths"]
    assert "/api/v1/ingestion/documents/{document_id}/retry/parsing" in payload["paths"]
    assert "/api/v1/ingestion/documents/{document_id}/retry/vector" in payload["paths"]
    assert "/api/v1/ingestion/documents/{document_id}/retry/extraction" in payload["paths"]
    assert "/api/v1/ingestion/documents/{document_id}/retry/graph" in payload["paths"]

    processing_stage_status = payload["components"]["schemas"]["ProcessingStageStatus"]
    assert "deferred" in processing_stage_status["enum"]
