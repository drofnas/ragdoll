from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
CONTRACT_SCRIPT = REPO_ROOT / "packages" / "tooling" / "scripts" / "generate_contracts.py"


def test_openapi_export_includes_auth_and_spaces_contracts(configured_database, tmp_path):
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

    assert "/api/v1/auth/register" in payload["paths"]
    assert "/api/v1/auth/login" in payload["paths"]
    assert "/api/v1/auth/me" in payload["paths"]
    assert "/api/v1/spaces" in payload["paths"]
    assert "/api/v1/spaces/{space_id}" in payload["paths"]

    schemas = payload["components"]["schemas"]
    assert "RegisterRequest" in schemas
    assert "LoginTokenResponse" in schemas
    assert "UserProfileResponse" in schemas
    assert "SpaceResponse" in schemas
    assert "ProblemResponse" in schemas

    login_request = payload["paths"]["/api/v1/auth/login"]["post"]["requestBody"]["content"]
    assert "application/x-www-form-urlencoded" in login_request
