from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
CONTRACT_SCRIPT = REPO_ROOT / "packages" / "tooling" / "scripts" / "generate_contracts.py"


def test_openapi_export_includes_phase10_contracts(configured_database, tmp_path):
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

    assert "/api/v1/chat/sessions" in payload["paths"]
    assert "/api/v1/chat/sessions/{session_id}/messages" in payload["paths"]
    assert "/api/v1/tracked-state/summary" in payload["paths"]
    assert "/api/v1/changes/{change_id}/read" in payload["paths"]
    assert "/api/v1/corrections/{correction_id}/verify" in payload["paths"]

    schemas = payload["components"]["schemas"]
    assert "ChatSendMessageResponse" in schemas
    assert "TrackedFieldSummary" in schemas
    assert "ChangeEventDetail" in schemas
    assert "CorrectionRecordResponse" in schemas
