from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_FLOOR1_REPARTITIONED_024"
PREVIOUS = BASE / "HA_TWO_FLOOR_FLOOR1_TEN_ROUTES_REPAIRED_023"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR1_REPARTITION_CERTIFIED_025"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_REPARTITION_CERTIFIED_025.zip"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest().upper()


def body_digest(route: dict) -> str:
    return digest([[coordinate * 100 for coordinate in point] for point in route["heating_body_points_grid"]])


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D025 is append-only")
    model = json.loads((SOURCE / "canonical_geometry.json").read_text(encoding="utf-8"))
    previous = json.loads((PREVIOUS / "canonical_geometry.json").read_text(encoding="utf-8"))
    previous_routes = {route["route_id"]: route for route in previous["routes"]}
    changed_ids = {"F1-C03", "F1-C04"}
    lineage = []
    for route in model["routes"]:
        old = previous_routes[route["route_id"]]
        old_digest = body_digest(old)
        current_digest = body_digest(route)
        changed = route["route_id"] in changed_ids
        if changed != (old["heating_body_points_grid"] != route["heating_body_points_grid"]):
            raise RuntimeError(f"lineage mismatch for {route['route_id']}")
        route["heating_body_digest"] = current_digest
        lineage.append(
            {
                "route_id": route["route_id"],
                "changed": changed,
                "source_body_digest_mm": old_digest,
                "current_body_digest_mm": current_digest,
                "reason": "SMALL_WC_REPARTITION" if changed else "BODY_GEOMETRY_PRESERVED",
            }
        )
    model.pop("source_body_preservation", None)
    model["body_lineage"] = lineage
    model["body_digest_coordinate_space"] = "ORDERED_POINTS_MM"
    model.update(
        artifact_id="HA_TWO_FLOOR_FLOOR1_REPARTITION_CERTIFIED_025",
        status="D024_GEOMETRY_AND_BODY_LINEAGE_PASS_REWORK_HALL_COVERAGE",
        derived_from_artifact_id="HA_TWO_FLOOR_FLOOR1_REPARTITIONED_024",
        derived_from_geometry_digest=json.loads((SOURCE / "canonical_geometry.json").read_text(encoding="utf-8"))["geometry_digest"],
    )
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)
    validation = json.loads((SOURCE / "validation.json").read_text(encoding="utf-8"))
    validation.update(
        artifact_id=model["artifact_id"],
        status=model["status"],
        body_digest_coordinate_space="ORDERED_POINTS_MM",
        body_lineage_changed_ids=sorted(changed_ids),
        body_lineage_preserved_ids=[item["route_id"] for item in lineage if not item["changed"]],
        body_lineage_validation="PASS",
        ordered_route_geometry_changed_from_D024=False,
    )
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(SOURCE / "k1_repartitioned_gate_contract.json", OUTPUT / "k1_repartitioned_gate_contract.json")
    shutil.copy2(SOURCE / "floor_1_repartitioned_overlay.png", OUTPUT / "floor_1_repartitioned_overlay.png")
    shutil.copy2(SOURCE / "floor_1_repartitioned_pipes_only.png", OUTPUT / "floor_1_repartitioned_pipes_only.png")
    (OUTPUT / "report.md").write_text(
        "# D025\n\nD024 route geometry is preserved exactly. Body digests are standardized to ordered millimetre coordinates. C03 and C04 are explicitly recorded as changed for SMALL_WC_REPARTITION; the remaining eight heating bodies are recorded as preserved. Hall/stair coverage remains unresolved.\n",
        encoding="utf-8",
    )
    files = [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({"artifact_id": model["artifact_id"], "geometry_digest": model["geometry_digest"], "files": files}, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "geometry_unchanged": True, "changed_bodies": sorted(changed_ids), "digest": model["geometry_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
