from __future__ import annotations

import codecs
import json
import sys
import tempfile
import unittest
from pathlib import Path

from agent.model_reader import (
    DUPLICATE_JSON_KEY_MESSAGE,
    JSON_NESTING_TOO_DEEP_MESSAGE,
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
