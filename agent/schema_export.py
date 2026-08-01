from __future__ import annotations

import argparse
import json
import sys

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from agent.project_models import CanonicalProjectModel
from agent.rooms_api import RoomExportReport


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA_DIRECTORY = ROOT_DIRECTORY / "schemas"

JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
SCHEMA_BASE_URI = "https://homeaura.local/schemas"


def _base_schema(
    model: type[BaseModel],
    *,
    file_name: str,
    title: str,
    contract_version: str,
    source_model: str,
) -> dict[str, Any]:
    schema = model.model_json_schema(mode="validation")
    schema["$schema"] = JSON_SCHEMA_DIALECT
    schema["$id"] = f"{SCHEMA_BASE_URI}/{file_name}"
    schema["title"] = title
    schema["x-homeaura-contract-version"] = contract_version
    schema["x-homeaura-source-model"] = source_model
    schema["x-homeaura-validation-scope"] = (
        "Structural JSON Schema. Runtime Pydantic model validators remain "
        "authoritative for cross-field and semantic invariants."
    )
    return schema


def build_room_schema() -> dict[str, Any]:
    schema = _base_schema(
        RoomExportReport,
        file_name="room.schema.json",
        title="HomeAura Rooms Export Contract",
        contract_version="1.1",
        source_model="agent.rooms_api.RoomExportReport",
    )

    format_version = schema["properties"]["FormatVersion"]
    format_version["enum"] = ["1.0", "1.1"]
    format_version["description"] = (
        "Supported rooms export format. Version 1.0 is retained for "
        "backward compatibility; version 1.1 is current."
    )
    schema["x-homeaura-supported-format-versions"] = ["1.0", "1.1"]
    schema["x-homeaura-unknown-field-policy"] = (
        "Ignored by the legacy runtime models for backward and forward "
        "compatibility."
    )
    return schema


def build_project_schema() -> dict[str, Any]:
    schema = _base_schema(
        CanonicalProjectModel,
        file_name="project.schema.json",
        title="HomeAura Canonical Project Contract",
        contract_version="1.0",
        source_model="agent.project_models.CanonicalProjectModel",
    )
    schema["x-homeaura-unknown-field-policy"] = (
        "Forbidden by strict project runtime models."
    )
    return schema


def build_contract_schemas() -> dict[str, dict[str, Any]]:
    return {
        "room.schema.json": build_room_schema(),
        "project.schema.json": build_project_schema(),
    }


def schema_json_bytes(schema: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            schema,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def write_contract_schemas(directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for file_name, schema in build_contract_schemas().items():
        path = directory / file_name
        path.write_bytes(schema_json_bytes(schema))
        written.append(path)
    return written


def check_contract_schemas(directory: Path) -> list[str]:
    errors: list[str] = []
    schemas = build_contract_schemas()
    for file_name, schema in schemas.items():
        path = directory / file_name
        expected = schema_json_bytes(schema)
        if not path.is_file():
            errors.append(f"missing generated schema: {path}")
            continue
        if path.read_bytes() != expected:
            errors.append(f"generated schema is stale: {path}")

    expected_file_names = set(schemas)
    actual_file_names = {
        path.name
        for path in directory.glob("*.schema.json")
        if path.is_file()
    }
    for file_name in sorted(actual_file_names - expected_file_names):
        errors.append(
            f"unexpected generated schema: {directory / file_name}"
        )
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export deterministic HomeAura room and project JSON Schemas."
        )
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=DEFAULT_SCHEMA_DIRECTORY,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when exported schemas are missing or stale.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.check:
        errors = check_contract_schemas(args.output_directory)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        return 0

    for path in write_contract_schemas(args.output_directory):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
