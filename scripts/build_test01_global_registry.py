"""Build the Test_01 global preliminary registry and transit-load report.

Reads the authoritative room list from ``two_floor_summary.json`` and the
per-circuit coverage/transit/vertical numbers from ``circuit_schedule.json``,
then runs the planning layer ``agent.ufh_global_planner`` to produce:

- the complete 16-room registry with preliminary circuit counts,
- the manifold egress demand,
- the per-segment transit pipe load (manifold egress, riser, corridor<->boiler
  opening, and floor-1 / attic corridor branches).

Every unverified or missing input is kept as ``UNVERIFIED``/``BLOCKED``; no
number is promoted to a physically confirmed circuit.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.ufh_global_planner import (  # noqa: E402
    CorridorPassage,
    RoomRecord,
    build_global_preliminary_plan,
)

OUT = ROOT / "dev" / "ufh_real_plan"
SUMMARY_PATH = OUT / "two_floor_summary.json"
SCHEDULE_PATH = OUT / "circuit_schedule.json"

BOILER_ROOM_ID = "FLOOR_1_PLAN:2c35c0ccf04544b4:ROOM"

# Branch membership is derived from the measured preview transit polylines in
# building_ufh_summary.json: floor-1 rooms 6/7/8 enter the corridor on the left
# spine, rooms 1/2/3/5 on the central/right spine; attic rooms 14/15/16 enter
# on the left, 10/11/12/13 on the right.  These are geometry observations, not
# authorized routing, and are only used to report a per-segment load split.
FLOOR1_LEFT = [
    "FLOOR_1_PLAN:4767e90a4e019716:ROOM",  # 6
    "FLOOR_1_PLAN:8c25b2af4cb28379:ROOM",  # 7
    "FLOOR_1_PLAN:c5b40c4d2c432677:ROOM",  # 8
]
FLOOR1_CENTRAL = [
    "FLOOR_1_PLAN:d82596ad96a4009a:ROOM",  # 1
    "FLOOR_1_PLAN:23e1c19b1e8cd7bd:ROOM",  # 2
    "FLOOR_1_PLAN:dbda1f3916917c37:ROOM",  # 3
    "FLOOR_1_PLAN:e8abc7453895cbf7:ROOM",  # 5
]
ATTIC_LEFT = [
    "ATTIC_PLAN:ea7ed4904468a1da:ROOM",    # 14
    "ATTIC_PLAN:112c14729a5a9ee7:ROOM",    # 15
    "ATTIC_PLAN:49c65e3abf362d77:ROOM",    # 16
    "ATTIC_PLAN:fd106b1227a87876:ROOM",    # 9
]
ATTIC_RIGHT = [
    "ATTIC_PLAN:9776f1f2c9664133:ROOM",    # 10
    "ATTIC_PLAN:c4f6e730556e69f2:ROOM",    # 11
    "ATTIC_PLAN:3d760ac099594432:ROOM",    # 12
    "ATTIC_PLAN:9386d71e1d28f2ee:ROOM",    # 13
]


def load_rooms() -> list[RoomRecord]:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    schedule = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))

    schedule_by_room: dict[str, dict] = {}
    for circuit in schedule:
        room_id = circuit["CIRCUIT_ID"].rsplit("/", 1)[0]
        schedule_by_room[room_id] = circuit

    rooms: list[RoomRecord] = []
    for item in summary["rooms"]:
        room_id = item["room_hypothesis_id"]
        floor_source = item["floor_source_id"]
        floor = 2 if floor_source == "ATTIC_PLAN" else 1
        geometry_status = item.get("geometry_status", "UNKNOWN")
        routing_status = item.get("routing_status", "UNKNOWN")
        circuit = schedule_by_room.get(room_id)

        coverage = None
        transit = None
        area = item.get("room_area_m2")
        if circuit is not None:
            coverage = float(circuit["COVERAGE_LENGTH"])
            transit = float(circuit["TRANSIT_LENGTH"])
            area = circuit.get("ROOM_AREA", area)

        vertical = 6.0 if floor == 2 else 0.0

        if geometry_status == "GEOMETRY_UNRESOLVED" and coverage is None:
            authority = "GEOMETRY_UNRESOLVED"
        elif geometry_status == "GEOMETRY_UNRESOLVED":
            authority = "UNVERIFIED_UNDER_STAIR_PREVIEW"
        else:
            authority = "SOURCE_ROOM_GEOMETRY"

        rooms.append(
            RoomRecord(
                zone_id=room_id,
                floor=floor,
                zone_type="ROOM" if floor_source in ("FLOOR_1_PLAN", "ATTIC_PLAN") else "UNKNOWN",
                label=item["label"],
                authority=authority,
                area_m2=area,
                coverage_length_m=coverage,
                transit_length_m=transit,
                vertical_length_m=vertical,
                geometry_status=geometry_status,
            )
        )
    return rooms


def build_passages(rooms: list[RoomRecord]) -> list[CorridorPassage]:
    all_ids = [r.zone_id for r in rooms]
    floor1_non_boiler = [r.zone_id for r in rooms if r.floor == 1 and r.zone_id != BOILER_ROOM_ID]
    attic = [r.zone_id for r in rooms if r.floor == 2]
    return [
        CorridorPassage("MANIFOLD-EGRESS", carrier_room_ids=all_ids),
        CorridorPassage("RISER-R1", carrier_room_ids=attic),
        CorridorPassage("OPENING-CORRIDOR-BOILER", carrier_room_ids=floor1_non_boiler),
        CorridorPassage("FLOOR-1-CORRIDOR", carrier_room_ids=floor1_non_boiler),
        CorridorPassage("FLOOR-1-CORRIDOR-LEFT", carrier_room_ids=FLOOR1_LEFT),
        CorridorPassage("FLOOR-1-CORRIDOR-CENTRAL", carrier_room_ids=FLOOR1_CENTRAL),
        CorridorPassage("ATTIC-CORRIDOR", carrier_room_ids=attic),
        CorridorPassage("ATTIC-CORRIDOR-LEFT", carrier_room_ids=ATTIC_LEFT),
        CorridorPassage("ATTIC-CORRIDOR-RIGHT", carrier_room_ids=ATTIC_RIGHT),
    ]


def render_markdown(plan: dict) -> str:
    lines: list[str] = []
    lines.append("# Test_01 глобальный реестр предварительных контуров и транзитной нагрузки")
    lines.append("")
    lines.append(
        f"Политика: предельная длина одного контура `{plan['policy_limit_m']:.1f} м` "
        "(подача + покрытие + обратка). Оценки предварительные; физическое подтверждение отсутствует."
    )
    lines.append("")
    lines.append("## Помещения и предварительные контуры")
    lines.append("")
    lines.append(
        "| № | Помещение | Этаж | Покрытие, м | Транзит, м | Вертикаль, м | "
        "Контуров | Мин. контуров | Концов труб | Статус |"
    )
    lines.append(
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---|"
    )
    for row in plan["room_estimates"]:
        count = row["count"] if row["count"] is not None else "—"
        label = row["label"].split(";")[0].strip().split("/")[0]
        status = "BLOCKED" if row["blocked"] else ("UNVERIFIED" if row["authority"].startswith("UNVERIFIED") else "PRELIMINARY")
        lines.append(
            f"| {label} | {row['label']} | {row['floor']} | "
            f"{row['coverage_length_m'] if row['coverage_length_m'] is not None else '—'} | "
            f"{row['transit_length_m'] if row['transit_length_m'] is not None else '—'} | "
            f"{row['vertical_length_m']:.1f} | {count} | {row['minimum_count']} | "
            f"{row['pipe_end_demand']} | {status} |"
        )
    lines.append("")
    md = plan["manifold_demand"]
    lines.append("## Требования коллектора")
    lines.append("")
    total_label = (
        str(plan["total_circuit_count"])
        if plan["total_circuit_count"] is not None
        else "не определён (есть BLOCKED)"
    )
    lines.append(
        f"- Контуров: `{total_label}` (минимально `{plan['minimum_total_circuit_count']}`).\n"
        f"- Концов: подача `{md['supply_ends']}`, обратка `{md['return_ends']}`, "
        f"всего `{md['total_pipe_ends']}`.\n"
        f"- Авторитетность подключения: `{md['connection_authority']}`."
    )
    lines.append("")
    lines.append("## Транзитная нагрузка по участкам")
    lines.append("")
    lines.append("| Участок | Подача | Обратка | Всего труб | Неразрешённых помещений |")
    lines.append("|---|---:|---:|---:|---:|")
    for passage in plan["passages"]:
        lines.append(
            f"| {passage['passage_id']} | {passage['supply_pipe_count']} | "
            f"{passage['return_pipe_count']} | {passage['pipe_count']} | "
            f"{passage['unresolved_room_count']} |"
        )
    lines.append("")
    lines.append(
        "Примечание: `MANIFOLD-EGRESS` не равен числу труб на каждом участке. "
        "Проём `OPENING-CORRIDOR-BOILER` несут только 7 помещений первого этажа "
        "(исключая котельную, контур которой локальный); мансардные контуры идут "
        "вверх через стояк `RISER-R1`, а не через этот проём."
    )
    lines.append("")
    lines.append("## Какие контуры проходят через проём коридор ↔ котельная")
    lines.append("")
    lines.append(
        "- Через проём идут только контуры 1-го этажа, не находящиеся в котельной: "
        "помещения 1, 2, 3, 5, 6, 7, 8 (14 предварительных контуров → 28 труб).\n"
        "- Контур котельной (помещение 4) локальный и этот проём не пересекает.\n"
        "- Мансардные контуры (9–16) уходят вверх через стояк `RISER-R1` в точке "
        "коллектора, поэтому этот проём они не пересекают."
    )
    lines.append("")
    lines.append("## Проверка стояка R1 (мансарда)")
    lines.append("")
    riser = next(p for p in plan["passages"] if p["passage_id"] == "RISER-R1")
    mansard = [r for r in plan["room_estimates"] if r["floor"] == 2]
    routed_mansard = [r for r in mansard if r["count"] is not None]
    routed_circuits = sum(r["count"] for r in routed_mansard)
    lines.append(
        f"- Маршрутизируемых мансардных контуров (предварительно): `{routed_circuits}` "
        f"→ `{routed_circuits * 2}` труб.\n"
        f"- Помещение 9 (39.9 м²) заблокировано: геометрия не разрешена, "
        f"минимально `{2}` трубы.\n"
        f"- Итого нижняя граница стояка: `{riser['supply_pipe_count']}` подача + "
        f"`{riser['return_pipe_count']}` обратка = `{riser['pipe_count']}` труб "
        f"(неразрешённых помещений: `{riser['unresolved_room_count']}`)."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    rooms = load_rooms()
    passages = build_passages(rooms)
    plan = build_global_preliminary_plan(rooms, passages)

    # Compare the preliminary riser expectation against the current (un-split)
    # riser_schedule.json so the discrepancy is recorded explicitly.
    riser = next(p for p in plan["passages"] if p["passage_id"] == "RISER-R1")
    current_riser = json.loads((OUT / "riser_schedule.json").read_text(encoding="utf-8"))
    current_riser_total = current_riser["risers"][0]["TOTAL_PIPE_COUNT"]
    riser_expectation = {
        "riser_id": "R1",
        "preliminary_mansard_circuits_lower_bound": riser["supply_pipe_count"],
        "preliminary_supply_pipes": riser["supply_pipe_count"],
        "preliminary_return_pipes": riser["return_pipe_count"],
        "preliminary_total_pipes_lower_bound": riser["pipe_count"],
        "current_schedule_total_pipes": current_riser_total,
        "under_sized_vs_preliminary": current_riser_total < riser["pipe_count"],
        "authority": "PRELIMINARY_UNVERIFIED",
        "note": (
            "The current riser schedule reserves one circuit per routed mansard "
            "room; the corrected preliminary count reserves per-circuit transit "
            "and therefore more circuits."
        ),
    }
    (OUT / "riser_preliminary_expectation.json").write_text(
        json.dumps(riser_expectation, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    (OUT / "global_registry.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "global_registry.md").write_text(render_markdown(plan), encoding="utf-8")

    print(f"rooms={len(rooms)}")
    print(f"total_circuit_count={plan['total_circuit_count']}")
    print(f"minimum_total_circuit_count={plan['minimum_total_circuit_count']}")
    print(f"manifold_total_pipe_ends={plan['manifold_demand']['total_pipe_ends']}")
    print(f"riser_preliminary_total_pipes={riser_expectation['preliminary_total_pipes_lower_bound']}")
    print(f"riser_current_total_pipes={riser_expectation['current_schedule_total_pipes']}")
    print(f"riser_under_sized={riser_expectation['under_sized_vs_preliminary']}")
    for passage in plan["passages"]:
        print(
            f"{passage['passage_id']}: supply={passage['supply_pipe_count']} "
            f"return={passage['return_pipe_count']} total={passage['pipe_count']} "
            f"unresolved={passage['unresolved_room_count']}"
        )


if __name__ == "__main__":
    main()
