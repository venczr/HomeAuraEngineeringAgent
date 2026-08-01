from __future__ import annotations

import codecs
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.model_reader import (
    DUPLICATE_JSON_KEY_MESSAGE,
    JSON_NESTING_TOO_DEEP_MESSAGE,
    MAX_SNAPSHOT_JSON_BYTES,
    SNAPSHOT_JSON_TOO_LARGE_MESSAGE,
    load_snapshot,
)


def snapshot_payload() -> dict[str, object]:
    return {
        "GeneratedAtUtc": "2026-08-01T00:00:00Z",
        "DrawingName": "test.dwg",
        "DrawingFullPath": "C:\\test.dwg",
        "AcadVersion": "test",
        "PluginVersion": "test",
        "Is64BitProcess": True,
        "DrawingUnits": "Meters",
        "Extents": {
            "Minimum": {},
            "Maximum": {},
        },
        "ModelSpaceEntityCount": 0,
        "Layers": [],
        "EntityTypes": [],
        "BlockDefinitions": [],
    }


class ModelReaderTests(unittest.TestCase):
    def test_snapshot_json_limit_is_ten_mib(self) -> None:
        self.assertEqual(10 * 1024 * 1024, MAX_SNAPSHOT_JSON_BYTES)

    def test_load_snapshot_accepts_exact_byte_limit_without_read_text(
        self,
    ) -> None:
        encoded = json.dumps(snapshot_payload()).encode("utf-8")
        exact_limit_payload = encoded + (
            b" " * (MAX_SNAPSHOT_JSON_BYTES - len(encoded))
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "exact-limit.json"
            path.write_bytes(exact_limit_payload)

            with patch.object(
                Path,
                "read_text",
                side_effect=AssertionError(
                    "unbounded text read is forbidden"
                ),
            ):
                loaded = load_snapshot(path)

        self.assertEqual("test.dwg", loaded.DrawingName)

    def test_load_snapshot_rejects_one_byte_over_limit_before_decode(
        self,
    ) -> None:
        marker = "sensitive-oversize-path"

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / marker
            path.write_bytes(
                b"\xff" * (MAX_SNAPSHOT_JSON_BYTES + 1)
            )

            with self.assertRaises(ValueError) as context:
                load_snapshot(path)

        self.assertEqual(
            SNAPSHOT_JSON_TOO_LARGE_MESSAGE,
            str(context.exception),
        )
        self.assertNotIn(marker, str(context.exception))

    def test_load_snapshot_normalizes_excessive_nesting(self) -> None:
        depth = sys.getrecursionlimit() * 2
        content = "[" * depth + "0" + "]" * depth

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "deep.json"
            path.write_text(content, encoding="utf-8")

            with self.assertRaises(ValueError) as context:
                load_snapshot(path)

        self.assertEqual(
            JSON_NESTING_TOO_DEEP_MESSAGE,
            str(context.exception),
        )
        self.assertNotIn("recursion", str(context.exception).casefold())

    def test_load_snapshot_accepts_utf8_with_optional_bom(self) -> None:
        encoded = json.dumps(snapshot_payload()).encode("utf-8")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, content in (
                ("plain.json", encoded),
                ("bom.json", codecs.BOM_UTF8 + encoded),
            ):
                with self.subTest(name=name):
                    path = root / name
                    path.write_bytes(content)

                    loaded = load_snapshot(path)

                    self.assertEqual("test.dwg", loaded.DrawingName)
                    self.assertEqual(0, loaded.ModelSpaceEntityCount)

    def test_load_snapshot_rejects_duplicate_keys_at_any_depth(
        self,
    ) -> None:
        valid = json.dumps(snapshot_payload())
        marker = "sensitive-duplicate-key-must-not-echo"
        duplicates = (
            valid.replace(
                '"DrawingName": "test.dwg"',
                (
                    '"DrawingName": "test.dwg", '
                    f'"{marker}": 1, "{marker}": 2'
                ),
                1,
            ),
            valid.replace(
                '"Minimum": {}',
                (
                    '"Minimum": {'
                    f'"{marker}": 1, "{marker}": 2'
                    '}'
                ),
                1,
            ),
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, content in enumerate(duplicates):
                with self.subTest(index=index):
                    path = root / f"duplicate-{index}.json"
                    path.write_text(content, encoding="utf-8")

                    with self.assertRaises(ValueError) as context:
                        load_snapshot(path)

                    self.assertEqual(
                        DUPLICATE_JSON_KEY_MESSAGE,
                        str(context.exception),
                    )
                    self.assertNotIn(marker, str(context.exception))


if __name__ == "__main__":
    unittest.main()
