import hashlib
import json
import shutil
import struct
import tempfile
import unittest

from pathlib import Path

from agent.floor_heating_svg_certificate import (
    EXPECTED_GEOMETRY_DIGEST,
    EXPECTED_SVG_SHA256,
    build_review_manifest,
    certify_exact_v2,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "projects" / "Test_01" / "exports" / "floor_heating_svg" / "HA-FH-VIS-001-v2"
REVIEW = ROOT / "projects" / "Test_01" / "exports" / "floor_heating_svg" / "HA-FH-VIS-001-v2-review-bundle-r3"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise AssertionError(f"invalid PNG header: {path}")
    return struct.unpack(">II", data[16:24])


class FloorHeatingSvgCertificateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.before = {path.name: sha256(path) for path in SOURCE.iterdir() if path.is_file()}
        cls.certificate = certify_exact_v2(SOURCE)

    @classmethod
    def tearDownClass(cls) -> None:
        after = {path.name: sha256(path) for path in SOURCE.iterdir() if path.is_file()}
        if cls.before != after:
            raise AssertionError("certificate tests modified the exact v2 artifacts")

    def test_exact_artifact_identity(self) -> None:
        identity = self.certificate["artifact_identity"]
        self.assertEqual(identity["source_hashes"]["floor_heating_layout.svg"], EXPECTED_SVG_SHA256)
        self.assertEqual(identity["geometry_digest"], EXPECTED_GEOMETRY_DIGEST)
        self.assertEqual(identity["status"], "PASS")

    def test_topology_certificate_is_complete(self) -> None:
        topology = self.certificate["topology"]
        self.assertEqual(topology["status"], "PASS")
        self.assertEqual(topology["inter_circuit_crossing_count"], 0)
        self.assertEqual(len(topology["circuits"]), 2)
        for circuit in topology["circuits"]:
            self.assertEqual(circuit["ordered_source_point_count"], 26)
            self.assertEqual(circuit["rendered_command_count"], 26)
            self.assertEqual(circuit["rendered_segment_count"], 25)
            self.assertEqual(circuit["connected_component_count"], 1)
            self.assertEqual(circuit["endpoint_count"], 2)
            self.assertEqual(circuit["branch_node_count"], 0)
            self.assertEqual(circuit["non_adjacent_self_intersection_count"], 0)
            self.assertEqual(circuit["room_boundary_violation_count"], 0)
            self.assertEqual(circuit["exclusion_intersection_count"], 0)
            self.assertEqual(circuit["length_delta_mm"], 0.0)
            self.assertTrue(circuit["valid"])

    def test_spacing_certificate_enumerates_every_declared_pair(self) -> None:
        spacing = self.certificate["spacing"]
        self.assertEqual(spacing["status"], "PASS")
        self.assertEqual(spacing["applicable_pair_count"], 24)
        self.assertEqual(spacing["perimeter_pair_count"], 6)
        self.assertEqual(spacing["field_pair_count"], 18)
        self.assertEqual(spacing["perimeter_observed_minimum_mm"], 100.0)
        self.assertEqual(spacing["perimeter_observed_maximum_mm"], 100.0)
        self.assertEqual(spacing["field_observed_minimum_mm"], 200.0)
        self.assertEqual(spacing["field_observed_maximum_mm"], 200.0)
        self.assertTrue(all(value["complete"] for value in spacing["route_completeness"]))
        self.assertTrue(all(value["first_line_pipe_matches"] and value["second_line_pipe_matches"] for value in spacing["records"]))

    def test_all_spacing_transitions_are_continuous(self) -> None:
        spacing = self.certificate["spacing"]
        self.assertEqual(spacing["transition_count"], 16)
        self.assertTrue(all(value["same_canonical_route"] for value in spacing["transitions"]))
        self.assertTrue(all(value["connected_without_gap"] for value in spacing["transitions"]))

    def test_collector_mapping_is_unique_and_directional(self) -> None:
        collector = self.certificate["collector"]
        self.assertEqual(collector["status"], "PASS")
        self.assertEqual(collector["duplicate_port_ownership"], {})
        self.assertEqual(len(collector["mapping"]), 2)
        for value in collector["mapping"]:
            self.assertTrue(value["supply_unique"])
            self.assertTrue(value["return_unique"])
            self.assertNotEqual(value["supply_port"], value["return_port"])

    def test_certificate_is_deterministic(self) -> None:
        second = certify_exact_v2(SOURCE)
        self.assertEqual(self.certificate, second)
        self.assertEqual(self.certificate["certificate_digest"], second["certificate_digest"])

    def test_tampered_svg_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "v2"
            shutil.copytree(SOURCE, copied)
            svg = copied / "floor_heating_layout.svg"
            svg.write_text(svg.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "BLOCKED_VISUAL_ARTIFACT_IDENTITY_MISMATCH"):
                certify_exact_v2(copied)

    def test_review_manifest_hashes_every_append_only_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            review = Path(temporary) / "review"
            review.mkdir()
            certificate_path = review / "exhaustive_geometry_certificate.json"
            certificate_path.write_text(json.dumps(self.certificate, sort_keys=True), encoding="utf-8")
            (review / "full-layout.png").write_bytes(b"test-png-evidence")
            manifest = build_review_manifest(SOURCE, review, self.certificate)
            by_name = {value["name"]: value for value in manifest["review_artifacts"]}
            self.assertEqual(by_name["full-layout.png"]["sha256"], sha256(review / "full-layout.png"))
            self.assertEqual(by_name["exhaustive_geometry_certificate.json"]["sha256"], sha256(certificate_path))
            self.assertEqual(manifest["source_svg_sha256"], EXPECTED_SVG_SHA256)

    def test_published_review_bundle_has_exact_source_provenance(self) -> None:
        provenance = json.loads((REVIEW / "capture_provenance.json").read_text(encoding="utf-8"))
        manifest = json.loads((REVIEW / "review_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(provenance["source_svg_sha256"], EXPECTED_SVG_SHA256)
        self.assertEqual(manifest["source_svg_sha256"], EXPECTED_SVG_SHA256)
        self.assertEqual(manifest["source_geometry_digest"], EXPECTED_GEOMETRY_DIGEST)
        self.assertEqual(manifest["certificate_status"], "PASS")
        self.assertEqual(provenance["capture_version"], "HA-FH-VIS-002/1.1")
        self.assertFalse(provenance["canonical_coordinate_modification"])
        self.assertEqual(len(provenance["capture_script_sha256"]), 64)
        self.assertEqual(len(provenance["captures"]), 6)
        self.assertTrue(all(not value["pipe_coordinate_modification"] for value in provenance["captures"]))
        by_name = {value["name"]: value for value in manifest["review_artifacts"]}
        for capture in provenance["captures"]:
            path = REVIEW / capture["name"]
            self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(
                png_size(path),
                (capture["output_width_px"], capture["output_height_px"]),
            )
            self.assertEqual(sha256(path), capture["png_sha256"])
            self.assertEqual(by_name[path.name]["sha256"], capture["png_sha256"])


if __name__ == "__main__":
    unittest.main()
