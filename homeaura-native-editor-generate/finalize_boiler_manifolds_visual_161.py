from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = PROPOSALS / "HA_TWO_FLOOR_BOILER_MANIFOLDS_DUAL_RISE_160"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_BOILER_MANIFOLDS_FINAL_VISUAL_161"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_BOILER_MANIFOLDS_FINAL_VISUAL_161.zip"
ARTIFACT_ID = OUTPUT.name


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def render(project: Path, output: Path, clean: bool) -> None:
    command = [
        "dotnet", "run", "--project", str(ROOT / "homeaura-native-editor" / "HomeAura.NativeEditor.csproj"),
        "-c", "Release", "--", "--export-png-clean" if clean else "--export-png", str(project), str(output),
    ]
    subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D161 is append-only")
    OUTPUT.mkdir(parents=True)
    floor_source = SOURCE / "HomeAura_Floor1_BoilerManifolds_D160.homeaura.json"
    attic_source = SOURCE / "HomeAura_Attic_DualRise_D160.homeaura.json"
    contract_source = SOURCE / "two_manifold_dual_rise_contract.json"
    floor1 = load(floor_source)
    attic = load(attic_source)
    contract = load(contract_source)

    k1 = next(item for item in floor1["collectors"] if item["id"] == "K1")
    k2 = next(item for item in floor1["collectors"] if item["id"] == "K2")
    k1.update({"rotation_degrees": 0, "pipe_outlet_direction": "DOWN"})
    k2.update({"rotation_degrees": 180, "pipe_outlet_direction": "UP"})
    attic_k2 = next(item for item in attic["collectors"] if item["id"] == "K2")
    attic_k2.update({"rotation_degrees": 180, "pipe_outlet_direction": "UP", "visible_on_plan": False, "external_to_plan": True})
    floor1["service_zones"].append({
        "id": "K1-K2-SHARED-WALL-CABINET-D161",
        "floor_id": "FLOOR_1",
        "name": "Монтажная зона двух коллекторов",
        "outline": [
            {"x_mm": 16200, "y_mm": 8700}, {"x_mm": 18000, "y_mm": 8700},
            {"x_mm": 18000, "y_mm": 11400}, {"x_mm": 16200, "y_mm": 11400},
        ],
        "fill_color": "#115E59",
        "note": "Обе пары гребёнок на одной внутренней стене котельной. K2 показан перевёрнутым: петлевые выходы направлены вверх; сервисный доступ к расходомерам, воздухоотводчикам и приводам сохраняется.",
        "collector_id": "K2",
        "clear_height_mm": None,
        "pipe_capacity": 52,
    })
    floor1["training_metadata"]["notes"] = (
        "D161: два отдельных реальных символа гребёнок стоят один над другим на одной внутренней стене котельной. "
        "K1 обслуживает первый этаж выходами вниз; K2 перевёрнут на 180° и обслуживает мансарду выходами вверх. "
        "Толщины стен и голубые оконные проёмы редактируются независимо."
    )
    attic["training_metadata"]["notes"] = (
        "D161: физический K2 расположен в котельной первого этажа и на мансардном плане не дублируется. "
        "Шесть контуров идут через подъём у лестницы в гардеробную, восемь - через отдельную внутреннюю проходку котельной."
    )
    contract.update({
        "artifact_id": ARTIFACT_ID,
        "status": "TWO_BOILER_ROOM_MANIFOLDS_VISUAL_AND_DUAL_RISE_GEOMETRY_PASS_REWORK_HYDRAULICS",
        "source_D160_floor1_sha256": sha(floor_source),
        "source_D160_attic_sha256": sha(attic_source),
        "source_D160_contract_sha256": sha(contract_source),
        "manifold_plan_symbol": {
            "parallel_supply_and_return_headers": True,
            "flowmeters_drawn_on_supply_header": True,
            "return_valves_drawn": True,
            "K1_rotation_degrees": 0,
            "K1_pipe_outlet_direction": "DOWN",
            "K2_rotation_degrees": 180,
            "K2_pipe_outlet_direction": "UP",
            "same_mounting_wall_id": "FLOOR_1-W025",
            "drawing_is_plan_coordination_not_elevation": True,
        },
        "official_reference_urls": [
            "https://www.uponor.com/getmedia/f5bba18a-1193-45d5-bdbb-95e0eb743cc2/radiant%20floor%20heating%20installation%20handbook.pdf?sitename=Canada",
            "https://www.uponor.com/getmedia/c5ab8a1f-9f02-43a4-8bcb-3b6a186dafeb/underfloor-heating-install-guidepdf?sitename=UK",
            "https://www.caleffi.com/en-us/assembly-668s1-caleffi-6686c5s1a",
        ],
    })
    contract["boiler_room_manifolds"]["K1"] = k1
    contract["boiler_room_manifolds"]["K2"] = k2

    floor_file = OUTPUT / "HomeAura_Floor1_TwoManifolds_D161.homeaura.json"
    attic_file = OUTPUT / "HomeAura_Attic_TwoRise_D161.homeaura.json"
    dump(floor_file, floor1)
    dump(attic_file, attic)
    dump(OUTPUT / "two_manifold_final_contract.json", contract)
    dump(OUTPUT / "lineage.json", {
        "source_D160_floor1_sha256": sha(floor_source),
        "source_D160_attic_sha256": sha(attic_source),
        "route_geometry_changed": False,
        "wall_geometry_changed": False,
        "window_geometry_changed": False,
        "collector_symbol_orientation_changed": True,
    })
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID,
        "status": contract["status"],
        "floor1_collectors_in_boiler_room": 2,
        "same_mounting_wall": True,
        "K2_inverted_outlets_up": True,
        "attic_route_count": 14,
        "all_lengths_40_80m": True,
        "installation_ready": False,
        "remaining": "Hydraulic balancing and exact residual heating coverage review",
    })
    (OUTPUT / "README.md").write_text(
        "# D161 - два коллектора на одной стене котельной\n\n"
        "На плане первого этажа K1 и K2 показаны как две пары реальных гребёнок: подача с расходомерами и обратка с клапанами. "
        "K2 перевёрнут на 180 градусов, поэтому его петлевые выходы направлены вверх. Оба узла размещены на одной внутренней стене котельной.\n\n"
        "На мансарду предусмотрены две независимые ветви: шесть петель по полу под лестницей, вверх по дальней стене и через стену в гардеробную; "
        "восемь петель через отдельную проходку перекрытия из котельной в правую половину. Проектные длины с 3-м подъёмом - 56,2-76,2 м.\n",
        encoding="utf-8",
    )

    render(floor_file, OUTPUT / "HomeAura_Floor1_D161_Editor_View.png", False)
    render(floor_file, OUTPUT / "HomeAura_Floor1_D161_Clean_View.png", True)
    render(attic_file, OUTPUT / "HomeAura_Attic_D161_Editor_View.png", False)
    render(attic_file, OUTPUT / "HomeAura_Attic_D161_Clean_View.png", True)

    files = sorted(path for path in OUTPUT.iterdir() if path.is_file())
    dump(OUTPUT / "artifact_manifest.json", {
        "artifact_id": ARTIFACT_ID,
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    })
    with zipfile.ZipFile(PACKAGE, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUTPUT.iterdir()):
            if path.is_file():
                archive.write(path, path.name)
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "package_sha256": sha(PACKAGE),
        "files": len(list(OUTPUT.iterdir())),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
