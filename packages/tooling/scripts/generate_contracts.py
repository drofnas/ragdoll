#!/usr/bin/env python3
"""Scaffolded contract-generation entrypoint for the clean-room rebuild."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
API_SRC = REPO_ROOT / "apps" / "api" / "src"

if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from ragdoll.main import create_app  # noqa: E402


DEFAULT_OPENAPI_OUTPUT = REPO_ROOT / "packages" / "contracts" / "openapi" / "ragdoll.openapi.json"
DEFAULT_TYPESCRIPT_MANIFEST = REPO_ROOT / "packages" / "contracts" / "typescript" / "manifest.json"


def serialize_path(path: Path) -> str:
    """Prefer repo-relative paths, but support outputs outside the repo root."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def export_openapi_schema(output_path: Path) -> Path:
    """Export the current FastAPI OpenAPI document to the requested path."""
    app = create_app()
    schema = app.openapi()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def write_typescript_manifest(output_path: Path, openapi_path: Path) -> Path:
    """Write a Phase 2 manifest describing the future TypeScript generation target."""
    manifest = {
        "status": "scaffold_only",
        "source": serialize_path(openapi_path),
        "output_directory": serialize_path(output_path.parent),
        "notes": [
            "Phase 2 fixes the generation path and ownership only.",
            "Replace this manifest with real generated TypeScript output when the chosen generator is introduced.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export OpenAPI from apps/api and scaffold the TypeScript contract output path."
    )
    parser.add_argument(
        "--openapi-output",
        type=Path,
        default=DEFAULT_OPENAPI_OUTPUT,
        help="Where to write the exported OpenAPI JSON.",
    )
    parser.add_argument(
        "--typescript-manifest",
        type=Path,
        default=DEFAULT_TYPESCRIPT_MANIFEST,
        help="Where to write the scaffold manifest for future TypeScript generation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    openapi_output = args.openapi_output.resolve()
    typescript_manifest = args.typescript_manifest.resolve()

    exported_path = export_openapi_schema(openapi_output)
    manifest_path = write_typescript_manifest(typescript_manifest, exported_path)

    print(f"Exported OpenAPI schema to {exported_path}")
    print(f"Wrote TypeScript scaffold manifest to {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
