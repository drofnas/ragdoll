import json
import re
import subprocess
from pathlib import Path

from fastapi import APIRouter

from ragdoll.api.v1.router import build_v1_router
from ragdoll.modules.registry import V1_MODULE_REGISTRY


REPO_ROOT = Path(__file__).resolve().parents[4]
CAPABILITY_MAP = REPO_ROOT / "docs" / "architecture" / "capability-map.md"
CONTRACT_SCRIPT = REPO_ROOT / "packages" / "tooling" / "scripts" / "generate_contracts.py"


def _expected_capability_modules() -> set[str]:
    text = CAPABILITY_MAP.read_text(encoding="utf-8")
    return set(re.findall(r"modules/([a-z_]+)", text))


def test_v1_registry_covers_every_capability_owner():
    expected = _expected_capability_modules()
    actual = {registration.module_name for registration in V1_MODULE_REGISTRY}
    assert actual == expected


def test_each_registered_module_imports_router_and_schema_module():
    for registration in V1_MODULE_REGISTRY:
        router = registration.load_router()
        registration.import_schemas_module()

        assert isinstance(router, APIRouter)
        assert router.prefix == registration.public_prefix


def test_v1_router_builds_with_all_registered_modules():
    router = build_v1_router()
    paths = {route.path for route in router.routes}

    assert isinstance(router, APIRouter)
    assert "/health" in paths


def test_contract_generation_script_exports_openapi_and_typescript_manifest(tmp_path: Path):
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
    assert openapi_output.exists()
    assert typescript_manifest.exists()

    openapi_payload = json.loads(openapi_output.read_text(encoding="utf-8"))
    manifest_payload = json.loads(typescript_manifest.read_text(encoding="utf-8"))

    assert openapi_payload["info"]["title"] == "Ragdoll API"
    assert "/api/v1/health" in openapi_payload["paths"]
    assert manifest_payload["status"] == "scaffold_only"
