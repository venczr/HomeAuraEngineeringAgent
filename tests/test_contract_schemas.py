from __future__ import annotations

import json
import tempfile
import unittest

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from agent.domain_adapter import adapt_rooms_payload
from agent.project_foundation import (
    build_project_seed,
    sheet_manifest_reference,
)
from agent.project_models import (
    CanonicalProjectModel,
    ProjectLifecycleStatus,
)
from agent.schema_export import (
    build_contract_schemas,
    check_contract_schemas,
    schema_json_bytes,
    write_contract_schemas,
)


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
SCHEMA_DIRECTORY = ROOT_DIRECTORY / "schemas"
ROOMS_V1_0_FIXTURE = (
    ROOT_DIRECTORY / "tests" / "fixtures" / "rooms_v1_0.json"
)
ROOMS_V1_1_EXAMPLE = (
    ROOT_DIRECTORY / "docs" / "examples" / "rooms.v1.1.example.json"
)
FIXED_TIME = datetime(
    2026,
    7,
    29,
    12,
    0,
    tzinfo=timezone.utc,
)


class ContractSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schemas = build_contract_schemas()

    def _canonical_project_payload(self) -> dict:
        rooms_payload = json.loads(
            ROOMS_V1_0_FIXTURE.read_text(encoding="utf-8")
        )
        domain = adapt_rooms_payload(
            rooms_payload,
            project_id="contract-schema-test",
        )
        seed = build_project_seed(
            domain,
            [],
            created_at=FIXED_TIME,
        )
        project = CanonicalProjectModel(
            project_id=domain.project.stable_id,
            revision=1,
            status=ProjectLifecycleStatus.BLOCKED,
            domain=domain,
            seed=seed,
            sheet_manifest=sheet_manifest_reference(),
        )
        return project.model_dump(mode="json")

    def test_exported_schemas_are_current(self) -> None:
        self.assertEqual([], check_contract_schemas(SCHEMA_DIRECTORY))
        for file_name, schema in self.schemas.items():
            path = SCHEMA_DIRECTORY / file_name
            self.assertEqual(path.read_bytes(), schema_json_bytes(schema))

    def test_schema_check_rejects_unexpected_generated_schema(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            for file_name, schema in self.schemas.items():
                (directory / file_name).write_bytes(
                    schema_json_bytes(schema)
                )

            (directory / "README.md").write_text(
                "schema documentation\n",
                encoding="utf-8",
            )
            self.assertEqual([], check_contract_schemas(directory))

            unexpected_z = directory / "z-obsolete.schema.json"
            unexpected_a = directory / "a-obsolete.schema.json"
            unexpected_z.write_text("{}\n", encoding="utf-8")
            unexpected_a.write_text("{}\n", encoding="utf-8")
            self.assertEqual(
                [
                    f"unexpected generated schema: {unexpected_a}",
                    f"unexpected generated schema: {unexpected_z}",
                ],
                check_contract_schemas(directory),
            )

    def test_schema_writer_publishes_exact_contract_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            expected_paths = [
                directory / file_name
                for file_name in self.schemas
            ]

            self.assertEqual(
                expected_paths,
                write_contract_schemas(directory),
            )
            self.assertEqual([], check_contract_schemas(directory))
            for file_name, schema in self.schemas.items():
                self.assertEqual(
                    schema_json_bytes(schema),
                    (directory / file_name).read_bytes(),
                )

    def test_schema_writer_failure_preserves_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            destination = directory / "room.schema.json"
            previous = b"previous schema bytes\n"
            destination.write_bytes(previous)

            with patch.object(
                Path,
                "replace",
                side_effect=OSError("replace failed"),
            ):
                with self.assertRaisesRegex(OSError, "replace failed"):
                    write_contract_schemas(directory)

            self.assertEqual(previous, destination.read_bytes())
            self.assertEqual(
                [],
                list(directory.glob(".room.schema.json.*.tmp")),
            )

    def test_exported_schemas_use_draft_2020_12(self) -> None:
        for schema in self.schemas.values():
            Draft202012Validator.check_schema(schema)
            self.assertEqual(
                "https://json-schema.org/draft/2020-12/schema",
                schema["$schema"],
            )

    def test_room_schema_accepts_supported_examples(self) -> None:
        validator = Draft202012Validator(
            self.schemas["room.schema.json"]
        )
        for path in (ROOMS_V1_0_FIXTURE, ROOMS_V1_1_EXAMPLE):
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                validator.validate(payload)

    def test_room_schema_rejects_unsupported_format_version(self) -> None:
        payload = json.loads(
            ROOMS_V1_1_EXAMPLE.read_text(encoding="utf-8")
        )
        payload["FormatVersion"] = "2.0"
        with self.assertRaises(ValidationError):
            Draft202012Validator(
                self.schemas["room.schema.json"]
            ).validate(payload)

    def test_room_schema_preserves_legacy_unknown_field_policy(
        self,
    ) -> None:
        payload = json.loads(
            ROOMS_V1_1_EXAMPLE.read_text(encoding="utf-8")
        )
        payload["FutureCompatibleField"] = {"enabled": True}
        Draft202012Validator(
            self.schemas["room.schema.json"]
        ).validate(payload)

    def test_project_schema_accepts_canonical_runtime_document(
        self,
    ) -> None:
        Draft202012Validator(
            self.schemas["project.schema.json"]
        ).validate(self._canonical_project_payload())

    def test_project_schema_rejects_unknown_root_field(self) -> None:
        schema = self.schemas["project.schema.json"]
        payload = {
            "schema_version": "1.0",
            "unknown": True,
        }
        errors = list(Draft202012Validator(schema).iter_errors(payload))
        self.assertTrue(
            any(
                error.validator == "additionalProperties"
                for error in errors
            )
        )

    def test_project_schema_rejects_incompatible_version(self) -> None:
        schema_version = self.schemas["project.schema.json"][
            "properties"
        ]["schema_version"]
        self.assertEqual("1.0", schema_version["const"])
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema_version).validate("2.0")

    def test_project_schema_rejects_incompatible_version_in_document(
        self,
    ) -> None:
        payload = self._canonical_project_payload()
        payload["schema_version"] = "2.0"
        with self.assertRaises(ValidationError):
            Draft202012Validator(
                self.schemas["project.schema.json"]
            ).validate(payload)


if __name__ == "__main__":
    unittest.main()
