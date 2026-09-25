from __future__ import annotations

import hashlib
import json
import os
import shutil
from copy import deepcopy
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Point, Polygon, box, mapping
from shapely.ops import unary_union


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
D153 = PROPOSALS / "HA_TWO_FLOOR_NATIVE_EDITOR_EXACT_HOUSE_153" / "HomeAura_Attic_ExactHouse_D153.homeaura.json"
D180 = PROPOSALS / "HA_TWO_FLOOR_ARCHITECTURE_BASELINE_180" / "HomeAura_TwoFloor_ArchitectureBaseline_D180.homeaura.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_ATTIC_SOURCE_WALL_DOMAINS_181"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_ATTIC_SOURCE_WALL_DOMAINS_181.zip"
PROJECT_NAME = "HomeAura_TwoFloor_SourceWallDomains_D181.homeaura.json"
CONTRACT_NAME = "attic_source_wall_domains_contract.json"
IMAGE_NAME = "HomeAura_Attic_D181_SourceWallDomains.png"

D153_SHA = "210B36EE163117F6266EBD9234962CCDC1D2035E8ED1A804C35E975C096911DA"
D180_SHA = "C9071982B1A9D96FE77532CEECF7DD22685EE7E05B3A3218AC440D61B776FD4A"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest().upper()


def polygon(record: dict) -> Polygon:
    return Polygon([(point["x_mm"], point["y_mm"]) for point in record["outline"]])


def dimensions(geometry) -> list[int]:
    x0, y0, x1, y1 = geometry.bounds
    return [int(x1 - x0), int(y1 - y0)]


def bounds(geometry) -> list[int]:
    return [int(value) for value in geometry.bounds]


def edge_records(domain_id: str, geometry: Polygon) -> list[dict]:
    result = []
    coordinates = list(geometry.exterior.coords)
    for index, (first, second) in enumerate(zip(coordinates, coordinates[1:]), start=1):
        x1, y1 = first
        x2, y2 = second
        if x1 == x2:
            midpoint = (y1 + y2) / 2
            outward_sign = 1 if geometry.contains(Point(x1 - 0.01, midpoint)) else -1
            result.append({
                "face_id": f"{domain_id}-FACE-{index:02d}",
                "domain_id": domain_id,
                "axis": "VERTICAL",
                "coordinate_mm": int(x1),
                "span_mm": [int(min(y1, y2)), int(max(y1, y2))],
                "outward_sign": outward_sign,
            })
        elif y1 == y2:
            midpoint = (x1 + x2) / 2
            outward_sign = 1 if geometry.contains(Point(midpoint, y1 - 0.01)) else -1
            result.append({
                "face_id": f"{domain_id}-FACE-{index:02d}",
                "domain_id": domain_id,
                "axis": "HORIZONTAL",
                "coordinate_mm": int(y1),
                "span_mm": [int(min(x1, x2)), int(max(x1, x2))],
                "outward_sign": outward_sign,
            })
        else:
            raise RuntimeError(f"D153 face is not axis-aligned: {domain_id} edge {index}")
    return result


def opposing_face_pairs(faces: list[dict], domains: dict[str, Polygon]) -> tuple[list[dict], list[int]]:
    open_pairs = []
    for index, first in enumerate(faces):
        for second in faces[index + 1:]:
            if first["domain_id"] == second["domain_id"] or first["axis"] != second["axis"]:
                continue
            negative, positive = sorted((first, second), key=lambda item: item["coordinate_mm"])
            if negative["outward_sign"] != 1 or positive["outward_sign"] != -1:
                continue
            overlap_start = max(negative["span_mm"][0], positive["span_mm"][0])
            overlap_end = min(negative["span_mm"][1], positive["span_mm"][1])
            separation = positive["coordinate_mm"] - negative["coordinate_mm"]
            if separation <= 0 or overlap_end <= overlap_start:
                continue
            if first["axis"] == "VERTICAL":
                candidate = box(negative["coordinate_mm"], overlap_start,
                                positive["coordinate_mm"], overlap_end)
            else:
                candidate = box(overlap_start, negative["coordinate_mm"],
                                overlap_end, positive["coordinate_mm"])
            blocked = any(
                candidate.intersection(geometry).area > 0.001
                for domain_id, geometry in domains.items()
                if domain_id not in {first["domain_id"], second["domain_id"]}
            )
            if not blocked:
                open_pairs.append((separation, negative, positive, overlap_start, overlap_end, candidate))

    distinct_separations = sorted({item[0] for item in open_pairs})
    if distinct_separations != [108, 140, 163, 216, 220, 221, 7628]:
        raise RuntimeError(f"Unexpected D153 opposing-face separations: {distinct_separations}")
    narrow_max = 221
    selected = [item for item in open_pairs if item[0] <= narrow_max]
    selected.sort(key=lambda item: (item[5].bounds[1], item[5].bounds[0], item[0], item[1]["domain_id"]))
    records = []
    for index, (separation, negative, positive, overlap_start, overlap_end, candidate) in enumerate(selected, start=1):
        adjacent = [negative["domain_id"], positive["domain_id"]]
        records.append({
            "candidate_id": f"ATTIC-FACE-GAP-{index:02d}",
            "classification": "ROOM_TO_STAIR_GAP_CANDIDATE" if "A-X-STAIR" in adjacent
                              else "INTER_ROOM_PARTITION_GAP_CANDIDATE",
            "source_face_ids": [negative["face_id"], positive["face_id"]],
            "adjacent_domain_ids": adjacent,
            "axis": negative["axis"],
            "gap_width_mm": separation,
            "face_overlap_span_mm": [overlap_start, overlap_end],
            "face_overlap_length_mm": overlap_end - overlap_start,
            "bbox_mm": bounds(candidate),
            "area_m2": candidate.area / 1_000_000,
            "gap_width_is_verified_wall_thickness": False,
            "openings_subtracted": False,
            "geojson": mapping(candidate),
            "_geometry": candidate,
        })
    return records, distinct_separations


def clean(records: list[dict]) -> list[dict]:
    return [{key: value for key, value in record.items() if key != "_geometry"} for record in records]


def render(source: dict, rooms: dict[str, Polygon], stair: Polygon, wall_components: list,
           face_pairs: list[dict], junctions: list[dict], exterior_residuals: list,
           footprint: Polygon, output: Path) -> None:
    width, height = 1500, 1100
    image = Image.new("RGB", (width, height), "#07151C")
    draw = ImageDraw.Draw(image, "RGBA")
    level = polygon(source["levels"][0])
    x0, y0, x1, y1 = level.bounds
    margin_x, top, bottom = 145, 150, 1010
    scale = min((width - 2 * margin_x) / (x1 - x0), (bottom - top) / (y1 - y0))

    def point(value):
        x, y = value
        return (round(margin_x + (x - x0) * scale), round(bottom - (y - y0) * scale))

    def polygon_points(geometry):
        return [point(value) for value in geometry.exterior.coords]

    regular = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 24)
    small = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 18)
    tiny = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 14)
    bold = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 30)

    draw.text((35, 24), "D181 · МАНСАРДА · ИСХОДНЫЕ КАНДИДАТЫ СТЕН/ПЕРЕГОРОДОК", font=bold, fill="#FFFFFF")
    draw.text((35, 64), "Только геометрический остаток D153 — без выдуманных проёмов, окон, отверстий и труб", font=regular, fill="#F6C86B")
    draw.text((35, 98), "Оранжевое = кандидатный домен; серое = внешний/неприсвоенный остаток; голубое = кандидат внешней грани", font=small, fill="#B7DCE8")

    draw.polygon(polygon_points(level), fill="#102630", outline="#B9D9E4", width=3)
    for geometry in exterior_residuals:
        draw.polygon(polygon_points(geometry), fill="#33404A", outline="#E07A7A", width=3)
        bx0, by0, bx1, by1 = geometry.bounds
        draw.line([point((bx0, by0)), point((bx1, by1))], fill="#C96A6A", width=3)
        draw.line([point((bx0, by1)), point((bx1, by0))], fill="#C96A6A", width=3)

    for geometry in wall_components:
        draw.polygon(polygon_points(geometry), fill="#E8892E99", outline="#FFB347", width=3)
    for record in junctions:
        draw.polygon(polygon_points(record["_geometry"]), fill="#FFD166CC", outline="#FFF0A6", width=2)

    # Paint the proven room domains over the candidate union so polygon holes are
    # respected even by Pillow's simple polygon rasterizer.
    room_colours = ["#20566B", "#245E73", "#295A68", "#24566C", "#2A6274", "#28596A", "#245D72", "#1F5366"]
    room_names = {item["id"]: item["name"] for item in source["rooms"]}
    for (room_id, geometry), colour in zip(rooms.items(), room_colours):
        draw.polygon(polygon_points(geometry), fill=colour, outline="#70A9BA", width=2)
        center = geometry.representative_point()
        label = f"{room_id}\n{room_names[room_id]}"
        draw.multiline_text(point((center.x, center.y)), label, font=tiny, fill="#E8F6FA", anchor="mm", align="center")

    for record in face_pairs:
        draw.polygon(polygon_points(record["_geometry"]), outline="#FFCF70", width=2)

    draw.polygon(polygon_points(stair), fill="#7A2935CC", outline="#FF7285", width=3)
    center = stair.representative_point()
    draw.multiline_text(point((center.x, center.y)), "A-X-STAIR\nПРОЁМ", font=small, fill="#FFFFFF", anchor="mm", align="center")
    draw.line(polygon_points(footprint), fill="#66D9EF", width=5, joint="curve")

    labelled_widths = set()
    for record in face_pairs:
        value = record["gap_width_mm"]
        if value in labelled_widths:
            continue
        labelled_widths.add(value)
        center = record["_geometry"].representative_point()
        draw.text(point((center.x, center.y)), f"{value} мм", font=tiny, fill="#FFF7D6", anchor="mm",
                  stroke_width=2, stroke_fill="#4D2B0B")

    draw.rectangle((28, 1027, width - 28, 1082), fill="#0B2029DD", outline="#355662")
    draw.text((45, 1038), "17 межгранных полос + 8 узлов = 2 кандидатных домена · ширины зазоров 108/140/163/216/220/221 мм · НЕ толщины стен",
              font=small, fill="#FFD78A")
    image.save(output)


def main() -> None:
    refresh_own_output = os.environ.get("HOMEAURA_REFRESH_D181_OWN_OUTPUT") == "1"
    if (OUTPUT.exists() or PACKAGE.exists()) and not refresh_own_output:
        raise FileExistsError("D181 is append-only")
    if refresh_own_output and not OUTPUT.exists():
        raise FileNotFoundError("D181 refresh requested before the owned output exists")
    if sha(D153) != D153_SHA or sha(D180) != D180_SHA:
        raise RuntimeError("D153 or D180 source hash changed")

    d153 = json.loads(D153.read_text(encoding="utf-8"))
    d180 = json.loads(D180.read_text(encoding="utf-8"))
    level = polygon(d153["levels"][0])
    rooms = {item["id"]: polygon(item) for item in d153["rooms"]}
    exclusions = {item["id"]: polygon(item) for item in d153["exclusions"]}
    if list(exclusions) != ["A-X-STAIR"] or len(rooms) != 8:
        raise RuntimeError("Unexpected D153 ATTIC source domains")
    stair = exclusions["A-X-STAIR"]
    domains = {**rooms, **exclusions}
    occupied = unary_union(list(domains.values())).intersection(level)
    residual = level.difference(occupied)
    residual_components = sorted(list(residual.geoms), key=lambda item: item.bounds[0])
    if len(residual_components) != 2 or round(residual.area) != 37_049_699:
        raise RuntimeError("Unexpected D153 level complement")

    faces = [face for domain_id, geometry in domains.items() for face in edge_records(domain_id, geometry)]
    pair_records, all_separations = opposing_face_pairs(faces, domains)
    face_pair_union = unary_union([item["_geometry"] for item in pair_records])
    remainder = residual.difference(face_pair_union)
    remainder_components = sorted(list(remainder.geoms), key=lambda item: item.area)
    junction_geometries = remainder_components[:-2]
    exterior_residuals = sorted(remainder_components[-2:], key=lambda item: item.bounds[0])
    if len(junction_geometries) != 8 or any(item.area >= 100_000 for item in junction_geometries):
        raise RuntimeError("Unexpected narrow junction decomposition")
    if [round(item.area) for item in exterior_residuals] != [13_763_371, 13_786_803]:
        raise RuntimeError("Unexpected broad residual decomposition")

    junction_records = []
    for index, geometry in enumerate(sorted(junction_geometries, key=lambda item: (item.bounds[1], item.bounds[0])), start=1):
        touching = [
            item["candidate_id"] for item in pair_records
            if geometry.boundary.intersection(item["_geometry"].boundary).length > 0.001
        ]
        junction_records.append({
            "candidate_id": f"ATTIC-NARROW-JUNCTION-{index:02d}",
            "classification": "AMBIGUOUS_NARROW_PARTITION_JUNCTION_CANDIDATE",
            "bbox_mm": bounds(geometry),
            "dimensions_mm": dimensions(geometry),
            "area_m2": geometry.area / 1_000_000,
            "touching_face_gap_candidate_ids": touching,
            "opening_or_threshold_present": "UNVERIFIED",
            "geojson": mapping(geometry),
            "_geometry": geometry,
        })

    wall_domain = unary_union([face_pair_union, *junction_geometries])
    wall_components = sorted(list(wall_domain.geoms), key=lambda item: item.bounds[0])
    exterior_union = unary_union(exterior_residuals)
    if len(wall_components) != 2 or round(wall_domain.area) != 9_499_525:
        raise RuntimeError("Unexpected candidate wall-domain union")
    if residual.symmetric_difference(unary_union([wall_domain, exterior_union])).area > 0.001:
        raise RuntimeError("Complement decomposition is not exact")
    footprint = level.difference(exterior_union)

    wall_component_records = []
    for index, geometry in enumerate(wall_components, start=1):
        adjacent = sorted(domain_id for domain_id, domain in domains.items()
                          if geometry.boundary.intersection(domain.boundary).length > 0.001)
        wall_component_records.append({
            "component_id": f"ATTIC-WALL-DOMAIN-CANDIDATE-{index:02d}",
            "side": "WEST" if index == 1 else "EAST",
            "classification": "SOURCE_DERIVED_WALL_OR_PARTITION_DOMAIN_CANDIDATE_NOT_MATERIALIZED_WALL",
            "bbox_mm": bounds(geometry),
            "area_m2": geometry.area / 1_000_000,
            "adjacent_domain_ids": adjacent,
            "connected_component_preserved": True,
            "geojson": mapping(geometry),
        })

    broad_records = [{
        "component_id": f"ATTIC-BROAD-RESIDUAL-{index:02d}",
        "side": "WEST" if index == 1 else "EAST",
        "classification": "EXTERIOR_OR_UNASSIGNED_LEVEL_RESIDUAL_GEOMETRIC_INFERENCE",
        "bbox_mm": bounds(geometry),
        "dimensions_mm": dimensions(geometry),
        "area_m2": geometry.area / 1_000_000,
        "semantics_source_verified": False,
        "not_a_wall_domain": True,
        "geojson": mapping(geometry),
    } for index, geometry in enumerate(exterior_residuals, start=1)]

    envelope_points = [[int(x), int(y)] for x, y in footprint.exterior.coords]
    contract = {
        "schema": "homeaura.attic.source_wall_domains.v1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_SOURCE_WALL_DOMAINS_181",
        "status": "EXACT_COMPLEMENT_DOMAIN_CANDIDATES_ONLY_NOT_INSTALLATION_READY",
        "append_only_successor_of": "HA_TWO_FLOOR_ARCHITECTURE_BASELINE_180",
        "source_provenance": {
            "D180_project": {"path": str(D180.relative_to(ROOT)).replace("\\", "/"), "sha256": D180_SHA,
                             "selection": "COMPLETE_PROJECT_BASELINE"},
            "D153_attic_project": {"path": str(D153.relative_to(ROOT)).replace("\\", "/"), "sha256": D153_SHA,
                                   "selection": ["ATTIC_LEVEL_OUTLINE", "EIGHT_FINISH_FACE_ROOM_POLYGONS", "A_X_STAIR"]},
        },
        "method": {
            "exact_operation": "ATTIC_LEVEL_OUTLINE_MINUS_UNION(EIGHT_FINISH_FACE_ROOMS,A_X_STAIR)",
            "coordinate_precision_mm": 1,
            "source_semantics_not_inferred_as_fact": ["WALL_THICKNESS", "WALL_MATERIAL", "WINDOW", "DOOR_OPENING", "THRESHOLD_OPENING", "SLAB_HOLE", "PENETRATION"],
            "narrow_face_pair_rule": "OPEN_OPPOSING_SOURCE_FACES_WITH_108_TO_221_MM_SEPARATION",
            "narrow_rule_basis": "SOURCE_DERIVED_SEPARATIONS_HAVE_A_GAP_FROM_221_MM_TO_7628_MM; THIS IS A GEOMETRIC CLASSIFIER, NOT A NORMATIVE WALL THICKNESS",
            "all_positive_open_opposing_face_separations_mm": all_separations,
            "junction_rule": "EIGHT_SMALL REMAINDER COMPONENTS AFTER FACE-GAP SUBTRACTION; SEMANTICS REMAIN AMBIGUOUS",
            "broad_residual_rule": "TWO_LARGEST REMAINDER COMPONENTS; EXTERIOR/UNASSIGNED CLASSIFICATION IS GEOMETRIC INFERENCE",
        },
        "area_balance_m2": {
            "level_outline": level.area / 1_000_000,
            "finish_face_rooms": unary_union(list(rooms.values())).area / 1_000_000,
            "stair_within_level": stair.intersection(level).area / 1_000_000,
            "complete_residual": residual.area / 1_000_000,
            "face_gap_candidates": face_pair_union.area / 1_000_000,
            "narrow_junction_candidates": unary_union(junction_geometries).area / 1_000_000,
            "wall_partition_candidate_union": wall_domain.area / 1_000_000,
            "broad_exterior_or_unassigned_residual": exterior_union.area / 1_000_000,
            "balance_error_m2": (occupied.area + wall_domain.area + exterior_union.area - level.area) / 1_000_000,
        },
        "complete_residual": {
            "component_count": 2,
            "components": [{"component_id": f"ATTIC-LEVEL-COMPLEMENT-{index:02d}", "bbox_mm": bounds(item),
                            "area_m2": item.area / 1_000_000, "geojson": mapping(item)}
                           for index, item in enumerate(residual_components, start=1)],
        },
        "opposing_finish_face_gap_candidates": clean(pair_records),
        "opposing_finish_face_gap_candidate_count": len(pair_records),
        "narrow_junction_candidates": clean(junction_records),
        "narrow_junction_candidate_count": len(junction_records),
        "wall_partition_candidate_domains": wall_component_records,
        "wall_partition_candidate_domain_count": len(wall_component_records),
        "broad_exterior_or_unassigned_residuals": broad_records,
        "broad_exterior_or_unassigned_residual_count": len(broad_records),
        "exterior_envelope_face_candidate": {
            "classification": "T_SHAPED_FINISH_ENVELOPE_FACE_CANDIDATE_NOT_WALL_SOLID",
            "derivation": "BOUNDARY(LEVEL_MINUS_TWO_BROAD_RESIDUALS)",
            "semantics_source_verified": False,
            "wall_thickness_mm": None,
            "ordered_closed_points_mm": envelope_points,
            "geojson": mapping(footprint.boundary),
        },
        "materialization_boundary": {
            "ATTIC_project_wall_count_added": 0,
            "ATTIC_project_window_count_added": 0,
            "ATTIC_project_opening_count_added": 0,
            "ATTIC_project_hole_or_penetration_count_added": 0,
            "K2_route_count_added": 0,
            "sleeves_added": False,
            "walls": "CANDIDATE_DOMAINS_ONLY_NOT_MATERIALIZED",
            "windows": "NOT_MATERIALIZED_UNVERIFIED",
            "door_and_threshold_openings": "NOT_MATERIALIZED_UNVERIFIED",
            "slab_holes_and_penetrations": "NOT_MATERIALIZED_UNVERIFIED",
            "installation_ready": False,
        },
        "training_metadata_exception": {
            "D180_metadata_disposition": "SUPERSEDED_STALE_D176_ROUTE_DESCRIPTION",
            "D181_project_geometry_changed": False,
            "D181_training_metadata_only_exception": True,
        },
        "installation_ready": False,
        "next_block": "VERIFY_ATTIC_WALL_SOLIDS_THICKNESSES_OPENINGS_WINDOWS_AND_HOLES_BEFORE_ANY_ROUTE",
    }
    contract["contract_digest"] = digest(contract)

    project = deepcopy(d180)
    project["training_metadata"] = {
        "label": "DRAFT",
        "notes": "D181 preserves D180 geometry. ATTIC wall/partition shapes exist only in the external exact-complement candidate contract; no ATTIC wall, window, door, threshold, hole, penetration, sleeve, or K2 route is materialized.",
        "author_intent": "Source-derived ATTIC architecture audit only; verify physical construction and openings before routing.",
    }

    OUTPUT.mkdir(parents=True, exist_ok=refresh_own_output)
    (OUTPUT / PROJECT_NAME).write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / CONTRACT_NAME).write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    render(d153, rooms, stair, wall_components, pair_records, junction_records, exterior_residuals,
           footprint, OUTPUT / IMAGE_NAME)
    (OUTPUT / "README.md").write_text(
        "# D181 · кандидатные домены стен мансарды\n\n"
        "D181 не материализует стены. Он точно вычитает восемь finish-face полигонов помещений и `A-X-STAIR` из контура ATTIC D153. "
        "Остаток распадается на две компоненты. В них геометрически выделены 17 узких межгранных полос, 8 малых узлов и 2 большие нижние области. "
        "Узкие области объединены в два **кандидатных** домена стен/перегородок; их ширины 108–221 мм являются расстояниями между чистовыми гранями, а не подтверждёнными толщинами стен.\n\n"
        "Две большие области помечены только как внешний/неприсвоенный остаток. Кандидат внешней T-образной грани — линия, не стеновой solid. "
        "Окна, двери, пороги, отверстия, проходки и конструкции не подтверждены. Труб и гильз не добавлено; `installation_ready=false`. "
        "D181 также заменяет только устаревшее описание D176 в `training_metadata`; вся геометрия проекта D180 сохранена.\n",
        encoding="utf-8",
    )
    status = {
        "artifact_id": "HA_TWO_FLOOR_ATTIC_SOURCE_WALL_DOMAINS_181",
        "result": "EXACT_COMPLEMENT_DOMAIN_CANDIDATES_ONLY_NOT_INSTALLATION_READY",
        "complete_residual_component_count": 2,
        "face_gap_candidate_count": 17,
        "narrow_junction_candidate_count": 8,
        "wall_partition_candidate_domain_count": 2,
        "ATTIC_walls_materialized": 0,
        "openings_and_holes": "UNVERIFIED",
        "K2_route_count_added": 0,
        "installation_ready": False,
    }
    (OUTPUT / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    files = sorted(path for path in OUTPUT.iterdir()
                   if path.is_file() and path.name != "artifact_manifest.json")
    manifest = {
        "artifact_id": "HA_TWO_FLOOR_ATTIC_SOURCE_WALL_DOMAINS_181",
        "append_only": True,
        "contract_digest": contract["contract_digest"],
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "project_sha256": sha(OUTPUT / PROJECT_NAME),
        "contract_digest": contract["contract_digest"],
        "residual_area_m2": residual.area / 1_000_000,
        "candidate_wall_area_m2": wall_domain.area / 1_000_000,
        "broad_residual_area_m2": exterior_union.area / 1_000_000,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
