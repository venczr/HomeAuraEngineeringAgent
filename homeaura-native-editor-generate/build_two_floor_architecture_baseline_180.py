from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"

SOURCE_D178 = (
    PROPOSALS
    / "HA_TWO_FLOOR_FLOOR1_BOILER_PAIR_178"
    / "HomeAura_Floor1_BoilerPair_D178.homeaura.json"
)
SOURCE_D153 = (
    PROPOSALS
    / "HA_TWO_FLOOR_NATIVE_EDITOR_EXACT_HOUSE_153"
    / "HomeAura_Attic_ExactHouse_D153.homeaura.json"
)
EXPECTED_D178_SHA256 = "424D79B33D7BE8F3B0898410386A70E221F831E9B65734C646008A1FDF09438F"
EXPECTED_D153_SHA256 = "210B36EE163117F6266EBD9234962CCDC1D2035E8ED1A804C35E975C096911DA"

ARTIFACT_ID = "HA_TWO_FLOOR_ARCHITECTURE_BASELINE_180"
OUTPUT = PROPOSALS / ARTIFACT_ID
PACKAGE = PROPOSALS / "packages" / f"{ARTIFACT_ID}.zip"
PROJECT_NAME = "HomeAura_TwoFloor_ArchitectureBaseline_D180.homeaura.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def dump(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def require_source(path: Path, expected_sha256: str) -> None:
    actual = sha(path)
    if actual != expected_sha256:
        raise RuntimeError(
            {
                "source_hash_mismatch": str(path),
                "expected_sha256": expected_sha256,
                "actual_sha256": actual,
            }
        )


def run_editor(project_path: Path, output_path: Path, command: str) -> None:
    args = [
        "dotnet",
        "run",
        "--project",
        str(ROOT / "homeaura-native-editor" / "HomeAura.NativeEditor.csproj"),
        "-c",
        "Release",
        "--",
        command,
        str(project_path),
        str(output_path),
    ]
    completed = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError(
            {"command": args, "stdout": completed.stdout, "stderr": completed.stderr}
        )


def build_project() -> tuple[dict, dict, dict]:
    require_source(SOURCE_D178, EXPECTED_D178_SHA256)
    require_source(SOURCE_D153, EXPECTED_D153_SHA256)
    floor1 = json.loads(SOURCE_D178.read_text(encoding="utf-8-sig"))
    attic_source = json.loads(SOURCE_D153.read_text(encoding="utf-8-sig"))

    if [item["id"] for item in floor1["levels"]] != ["FLOOR_1"]:
        raise RuntimeError("D178 no longer has the expected single FLOOR_1 level")
    if [item["id"] for item in attic_source["levels"]] != ["ATTIC"]:
        raise RuntimeError("D153 no longer has the expected single ATTIC level")
    if len(attic_source["rooms"]) != 8 or any(
        item["floor_id"] != "ATTIC" for item in attic_source["rooms"]
    ):
        raise RuntimeError("D153 ATTIC room boundary changed")
    if [item["id"] for item in attic_source["exclusions"]] != ["A-X-STAIR"]:
        raise RuntimeError("D153 ATTIC stair exclusion changed")

    k2 = next(item for item in floor1["collectors"] if item["id"] == "K2")
    if not (
        k2["floor_id"] == "FLOOR_1"
        and k2["served_floor_id"] == "ATTIC"
        and k2["rotation_degrees"] == 180
        and k2["mounting_wall_id"] == "FLOOR_1-W025"
    ):
        raise RuntimeError("D178 K2 same-wall inverted placement changed")

    project = copy.deepcopy(floor1)
    project["levels"].extend(copy.deepcopy(attic_source["levels"]))
    project["rooms"].extend(copy.deepcopy(attic_source["rooms"]))
    project["exclusions"].extend(copy.deepcopy(attic_source["exclusions"]))

    # The append-only architecture baseline may change exactly these three
    # collections. Every other top-level D178 property must remain semantically
    # identical; this prevents old D153 routes or guessed architecture leaking in.
    for key, value in floor1.items():
        if key not in {"levels", "rooms", "exclusions"} and project[key] != value:
            raise RuntimeError({"unexpected_D180_change": key})

    return project, floor1, attic_source


def attic_projection(project: dict) -> dict:
    """Create a render-only single-level view without inventing ATTIC objects."""
    result = copy.deepcopy(project)
    result["levels"] = [item for item in result["levels"] if item["id"] == "ATTIC"]
    result["rooms"] = [item for item in result["rooms"] if item["floor_id"] == "ATTIC"]
    result["exclusions"] = [
        item for item in result["exclusions"] if item["floor_id"] == "ATTIC"
    ]
    result["service_zones"] = []
    result["floor_build_ups"] = []
    result["walls"] = []
    result["windows"] = []
    result["collectors"] = []
    result["circuits"] = []
    return result


def deterministic_zip(payload_directory: Path, package_path: Path) -> None:
    with zipfile.ZipFile(package_path, "w") as archive:
        for path in sorted(payload_directory.iterdir(), key=lambda item: item.name):
            if not path.is_file():
                continue
            info = zipfile.ZipInfo(path.name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D180 is append-only")

    project, floor1, attic_source = build_project()
    temporary_root = ROOT / "tmp"
    temporary_root.mkdir(exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="D180_architecture_", dir=temporary_root))
    if staging.resolve().parent != temporary_root.resolve() or not staging.name.startswith(
        "D180_architecture_"
    ):
        raise RuntimeError("Unsafe D180 staging path")

    try:
        payload = staging / "artifact"
        payload.mkdir()
        project_path = payload / PROJECT_NAME
        dump(project_path, project)

        diagnostics_path = payload / "engineering_diagnostics.json"
        run_editor(project_path, diagnostics_path, "--export-diagnostics")
        diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8-sig"))
        attic_diagnostics = next(
            item
            for item in diagnostics["collector_served_floor_details"]
            if item["collector_id"] == "K2"
        )

        floor1_projection_path = staging / "floor1_projection.homeaura.json"
        attic_projection_path = staging / "attic_projection.homeaura.json"
        dump(floor1_projection_path, floor1)
        dump(attic_projection_path, attic_projection(project))
        run_editor(
            floor1_projection_path,
            payload / "HomeAura_Floor1_D180_Clean.png",
            "--export-png-clean",
        )
        run_editor(
            attic_projection_path,
            payload / "HomeAura_Attic_D180_Architecture_Clean.png",
            "--export-png-clean",
        )

        contract = {
            "schema": "homeaura.two_floor.architecture_baseline.v1",
            "artifact_id": ARTIFACT_ID,
            "status": "TWO_LEVEL_ARCHITECTURE_BASELINE_ONLY_NOT_INSTALLATION_READY",
            "append_only": True,
            "source_provenance": {
                "official_D178_project": {
                    "path": str(SOURCE_D178.relative_to(ROOT)).replace("\\", "/"),
                    "sha256": EXPECTED_D178_SHA256,
                    "selection": "COMPLETE_PROJECT_BASELINE",
                },
                "D153_attic_project": {
                    "path": str(SOURCE_D153.relative_to(ROOT)).replace("\\", "/"),
                    "sha256": EXPECTED_D153_SHA256,
                    "selection": [
                        "ATTIC_LEVEL",
                        "EIGHT_FINISH_FACE_ROOM_DOMAINS",
                        "A_X_STAIR_EXCLUSION",
                    ],
                    "explicitly_not_imported": [
                        "COLLECTORS",
                        "CIRCUITS",
                        "SERVICE_ZONES",
                        "WALLS",
                        "WINDOWS",
                    ],
                },
            },
            "D178_preservation": {
                "unchanged_top_level_properties_except": [
                    "levels",
                    "rooms",
                    "exclusions",
                ],
                "floor1_level_preserved": True,
                "floor1_rooms_preserved": len(floor1["rooms"]),
                "floor1_exclusions_preserved": len(floor1["exclusions"]),
                "walls_preserved": len(floor1["walls"]),
                "windows_preserved": len(floor1["windows"]),
                "collectors_preserved": len(floor1["collectors"]),
                "circuits_preserved": len(floor1["circuits"]),
            },
            "ATTIC_architecture": {
                "level": "MATERIALIZED_VERIFIED_FROM_D153",
                "finish_face_room_domains": "MATERIALIZED_VERIFIED_FROM_D153",
                "finish_face_room_count": len(attic_source["rooms"]),
                "finish_face_room_ids": [item["id"] for item in attic_source["rooms"]],
                "stair_exclusion": "MATERIALIZED_VERIFIED_FROM_D153",
                "stair_exclusion_id": "A-X-STAIR",
                "walls": "NOT_MATERIALIZED_UNVERIFIED",
                "windows": "NOT_MATERIALIZED_UNVERIFIED",
                "door_openings": "NOT_MATERIALIZED_UNVERIFIED",
                "slab_holes_and_penetrations": "NOT_MATERIALIZED_UNVERIFIED",
            },
            "K2": {
                "placement": "PRESERVED_FROM_D178",
                "installed_floor_id": "FLOOR_1",
                "served_floor_id": "ATTIC",
                "mounting_wall_id": "FLOOR_1-W025",
                "rotation_degrees": 180,
                "floor_heating_loops": "NOT_MATERIALIZED_UNVERIFIED",
                "floor_service_routes": "NOT_MATERIALIZED_UNVERIFIED",
                "interfloor_routes": "NOT_MATERIALIZED_UNVERIFIED",
                "collector_connection_tails": "NOT_MATERIALIZED_UNVERIFIED",
                "complete_route_count": 0,
            },
            "diagnostic_boundary": {
                "served_floor_references_pass": diagnostics[
                    "served_floor_references_pass"
                ],
                "attic_room_count": attic_diagnostics["room_count"],
                "attic_heating_body_count": attic_diagnostics["heating_body_count"],
                "attic_loop_circuit_count": attic_diagnostics["loop_circuit_count"],
                "attic_axis_circuit_count": attic_diagnostics["axis_circuit_count"],
                "materialized_heating_routes_pass": diagnostics[
                    "materialized_heating_routes_pass"
                ],
                "installation_completeness_pass": diagnostics[
                    "installation_completeness_pass"
                ],
            },
            "collector_continuous_route_count": 0,
            "sleeves_added": False,
            "installation_ready": False,
            "next_block": (
                "VERIFY_ATTIC_WALLS_WINDOWS_OPENINGS_AND_PENETRATIONS_BEFORE_ROUTING"
            ),
        }
        if not (
            contract["diagnostic_boundary"]["served_floor_references_pass"]
            and contract["diagnostic_boundary"]["attic_room_count"] == 8
            and contract["diagnostic_boundary"]["attic_heating_body_count"] == 0
            and not contract["diagnostic_boundary"]["materialized_heating_routes_pass"]
            and not contract["diagnostic_boundary"]["installation_completeness_pass"]
        ):
            raise RuntimeError({"unexpected_D180_diagnostics": contract["diagnostic_boundary"]})

        dump(payload / "two_floor_architecture_baseline_contract.json", contract)
        dump(
            payload / "status.json",
            {
                "artifact_id": ARTIFACT_ID,
                "result": contract["status"],
                "level_count": 2,
                "attic_finish_face_room_count": 8,
                "attic_wall_status": "NOT_MATERIALIZED_UNVERIFIED",
                "attic_window_status": "NOT_MATERIALIZED_UNVERIFIED",
                "attic_opening_and_hole_status": "NOT_MATERIALIZED_UNVERIFIED",
                "K2_complete_route_count": 0,
                "collector_continuous_route_count": 0,
                "installation_ready": False,
            },
        )
        (payload / "README.md").write_text(
            "# D180 · архитектурная двухэтажная основа без выдуманных труб\n\n"
            "D180 сохраняет официальный D178 целиком и добавляет из D153 только "
            "контур уровня `ATTIC`, восемь полигонов помещений по чистовым граням и "
            "исключение лестничного проёма `A-X-STAIR`. Старые контуры, сервисные "
            "зоны и коллектор из D153 не импортированы.\n\n"
            "Стены, окна, дверные проёмы, отверстия/проходки и все маршруты K2 на "
            "мансарде имеют явный статус `NOT_MATERIALIZED_UNVERIFIED`. K2 остаётся "
            "на той же стене котельной первого этажа, развёрнут на 180° и обслуживает "
            "ATTIC. Установочная готовность: **нет**; коллекторно-непрерывных "
            "маршрутов: **0**. Гильзы не добавлены.\n",
            encoding="utf-8",
        )

        payloads = sorted(
            path for path in payload.iterdir() if path.is_file() and path.name != "artifact_manifest.json"
        )
        dump(
            payload / "artifact_manifest.json",
            {
                "artifact_id": ARTIFACT_ID,
                "append_only": True,
                "files": [
                    {
                        "name": path.name,
                        "bytes": path.stat().st_size,
                        "sha256": sha(path),
                    }
                    for path in payloads
                ],
            },
        )

        staging_package = staging / f"{ARTIFACT_ID}.zip"
        deterministic_zip(payload, staging_package)
        PACKAGE.parent.mkdir(parents=True, exist_ok=True)
        payload.replace(OUTPUT)
        staging_package.replace(PACKAGE)
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    print(
        json.dumps(
            {
                "artifact": ARTIFACT_ID,
                "project_sha256": sha(OUTPUT / PROJECT_NAME),
                "package_sha256": sha(PACKAGE),
                "levels": 2,
                "attic_finish_face_rooms": 8,
                "attic_routes": 0,
                "collector_continuous_route_count": 0,
                "installation_ready": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
