#!/usr/bin/env python3
"""Contract-generation entrypoint for the clean-room rebuild."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import keyword
import re
import sys
from pathlib import Path
from typing import Any


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


def _to_pascal_case(value: str) -> str:
    parts = re.split(r"[^a-zA-Z0-9]+", value)
    normalized = "".join(part[:1].upper() + part[1:] for part in parts if part)
    return normalized or "GeneratedType"


def _is_valid_identifier(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", value)) and not keyword.iskeyword(value)


def _format_property_name(name: str) -> str:
    if _is_valid_identifier(name):
        return name
    return json.dumps(name)


def _ref_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def _schema_type_name(name: str) -> str:
    if _is_valid_identifier(name):
        return name
    return _to_pascal_case(name)


def _indent(level: int) -> str:
    return "  " * level


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _schema_to_typescript(schema: dict[str, Any] | None, level: int = 0) -> str:
    if schema is None:
        return "unknown"

    if "$ref" in schema:
        return _schema_type_name(_ref_name(schema["$ref"]))

    if "const" in schema:
        return json.dumps(schema["const"])

    if "enum" in schema:
        enum_values = " | ".join(json.dumps(value) for value in schema["enum"])
        return enum_values or "never"

    if "allOf" in schema:
        members = [_schema_to_typescript(member, level) for member in schema["allOf"]]
        return " & ".join(_dedupe_preserve_order(members)) or "unknown"

    if "anyOf" in schema:
        members = [_schema_to_typescript(member, level) for member in schema["anyOf"]]
        return " | ".join(_dedupe_preserve_order(members)) or "unknown"

    if "oneOf" in schema:
        members = [_schema_to_typescript(member, level) for member in schema["oneOf"]]
        return " | ".join(_dedupe_preserve_order(members)) or "unknown"

    schema_type = schema.get("type")

    if schema_type == "array":
        return f"Array<{_schema_to_typescript(schema.get('items', {}), level)}>"

    if schema_type == "object" or "properties" in schema or "additionalProperties" in schema:
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        additional_properties = schema.get("additionalProperties")

        if not properties and additional_properties not in (None, False):
            value_type = "unknown" if additional_properties is True else _schema_to_typescript(additional_properties, level)
            return f"Record<string, {value_type}>"

        if not properties:
            return "Record<string, unknown>"

        lines = ["{"]
        for property_name, property_schema in properties.items():
            optional = "" if property_name in required else "?"
            lines.append(
                f"{_indent(level + 1)}{_format_property_name(property_name)}{optional}: "
                f"{_schema_to_typescript(property_schema, level + 1)};"
            )

        if additional_properties not in (None, False):
            value_type = "unknown" if additional_properties is True else _schema_to_typescript(additional_properties, level + 1)
            lines.append(f"{_indent(level + 1)}[key: string]: {value_type};")

        lines.append(f"{_indent(level)}}}")
        return "\n".join(lines)

    if schema_type == "string":
        if schema.get("format") == "binary":
            return "Blob"
        return "string"

    if schema_type in {"integer", "number"}:
        return "number"

    if schema_type == "boolean":
        return "boolean"

    if schema_type == "null":
        return "null"

    return "unknown"


def _parameters_to_typescript(parameters: list[dict[str, Any]]) -> tuple[str, str]:
    grouped: dict[str, list[dict[str, Any]]] = {"path": [], "query": []}
    for parameter in parameters:
        location = parameter.get("in")
        if location in grouped:
            grouped[location].append(parameter)

    def render(location: str) -> str:
        entries = grouped[location]
        if not entries:
            return "never"
        lines = ["{"]
        for parameter in entries:
            parameter_name = parameter["name"]
            optional = "" if parameter.get("required", False) else "?"
            schema = parameter.get("schema", {})
            lines.append(
                f"  {_format_property_name(parameter_name)}{optional}: {_schema_to_typescript(schema, 1)};"
            )
        lines.append("}")
        return "\n".join(lines)

    return render("path"), render("query")


def _request_body_details(operation: dict[str, Any]) -> tuple[str, str]:
    request_body = operation.get("requestBody")
    if not request_body:
        return "never", "never"

    content = request_body.get("content", {})
    if not content:
        return "unknown", "never"

    content_type, payload = next(iter(content.items()))
    return _schema_to_typescript(payload.get("schema", {}), 0), json.dumps(content_type)


def _response_details(operation: dict[str, Any]) -> tuple[str, str]:
    responses = operation.get("responses", {})
    if not responses:
        return "{}", "unknown"

    rendered_responses: list[str] = []
    success_response: str = "unknown"
    success_code: int | None = None

    for status_code, payload in sorted(responses.items(), key=lambda item: item[0]):
        content = payload.get("content", {})
        json_payload = content.get("application/json")
        schema = json_payload.get("schema") if json_payload else None
        if schema is None:
            media_type, media_payload = next(iter(content.items()), (None, None))
            schema = media_payload.get("schema") if media_payload else None
            if media_type and schema is None and media_type != "application/json":
                rendered = "Blob"
            else:
                rendered = _schema_to_typescript(schema, 0)
        else:
            rendered = _schema_to_typescript(schema, 0)

        if status_code.isdigit():
            status_number = int(status_code)
            rendered_responses.append(f"  {status_code}: {rendered};")
            if 200 <= status_number < 300 and (success_code is None or status_number < success_code):
                success_code = status_number
                success_response = rendered
        else:
            rendered_responses.append(f"  {json.dumps(status_code)}: {rendered};")

    response_block = "{\n" + "\n".join(rendered_responses) + "\n}"
    return response_block, success_response


def _build_component_types(openapi_schema: dict[str, Any]) -> str:
    schemas = openapi_schema.get("components", {}).get("schemas", {})
    if not schemas:
        return ""

    blocks: list[str] = []
    for name, schema in sorted(schemas.items()):
        rendered = _schema_to_typescript(schema, 0)
        type_name = _schema_type_name(name)
        if rendered.startswith("{\n"):
            blocks.append(f"export interface {type_name} {rendered}")
        else:
            blocks.append(f"export type {type_name} = {rendered};")
    return "\n\n".join(blocks)


def _build_operation_types(openapi_schema: dict[str, Any]) -> str:
    paths = openapi_schema.get("paths", {})
    operation_blocks: list[str] = []
    operation_refs: list[str] = []

    for path_name, methods in sorted(paths.items()):
        for method, operation in sorted(methods.items()):
            operation_id = operation.get("operationId") or f"{method}_{path_name}"
            interface_name = f"{_to_pascal_case(operation_id)}Operation"
            path_params, query_params = _parameters_to_typescript(operation.get("parameters", []))
            request_body, request_content_type = _request_body_details(operation)
            responses, success_response = _response_details(operation)

            operation_refs.append(f"  {json.dumps(operation_id)}: {interface_name};")
            operation_blocks.append(
                "\n".join(
                    [
                        f"export interface {interface_name} {{",
                        f"  method: {json.dumps(method)};",
                        f"  path: {json.dumps(path_name)};",
                        f"  pathParams: {path_params};",
                        f"  queryParams: {query_params};",
                        f"  requestBody: {request_body};",
                        f"  requestContentType: {request_content_type};",
                        f"  responses: {responses};",
                        f"  successResponse: {success_response};",
                        "}",
                    ]
                )
            )

    if not operation_blocks:
        return ""

    operation_map = "export interface ApiOperations {\n" + "\n".join(operation_refs) + "\n}"
    return "\n\n".join([operation_map, *operation_blocks])


def render_typescript_contracts(openapi_schema: dict[str, Any]) -> str:
    schema_block = _build_component_types(openapi_schema)
    operation_block = _build_operation_types(openapi_schema)
    sections = [
        "/* eslint-disable */",
        "// This file is generated by packages/tooling/scripts/generate_contracts.py.",
        "// Do not edit by hand.",
    ]
    if schema_block:
        sections.append(schema_block)
    if operation_block:
        sections.append(operation_block)
    return "\n\n".join(sections) + "\n"


def write_typescript_artifacts(output_path: Path, openapi_path: Path, openapi_schema: dict[str, Any]) -> Path:
    """Write generated TypeScript contracts plus a manifest describing the output."""
    output_directory = output_path.parent
    output_directory.mkdir(parents=True, exist_ok=True)

    index_path = output_directory / "index.ts"
    index_path.write_text(render_typescript_contracts(openapi_schema), encoding="utf-8")

    schema_count = len(openapi_schema.get("components", {}).get("schemas", {}))
    operation_count = sum(len(methods) for methods in openapi_schema.get("paths", {}).values())
    manifest = {
        "status": "generated",
        "source": serialize_path(openapi_path),
        "output_directory": serialize_path(output_directory),
        "entrypoint": serialize_path(index_path),
        "schema_count": schema_count,
        "operation_count": operation_count,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "notes": [
            "TypeScript contracts are generated from the exported OpenAPI document.",
            "Feature clients should remain thin wrappers around shared transport rather than generated request helpers.",
        ],
    }
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

    app = create_app()
    schema = app.openapi()

    openapi_output.parent.mkdir(parents=True, exist_ok=True)
    openapi_output.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path = write_typescript_artifacts(typescript_manifest, openapi_output, schema)

    print(f"Exported OpenAPI schema to {openapi_output}")
    print(f"Wrote TypeScript contract manifest to {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
