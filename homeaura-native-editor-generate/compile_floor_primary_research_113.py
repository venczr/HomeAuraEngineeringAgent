from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_RESEARCH_113"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR_PRIMARY_RESEARCH_113.zip"
SOURCE_D109 = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_INTEGRATION_109" / "floor_primary_integration.json"
SOURCE_D112 = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_INSTALLATION_SHEET_112" / "installation_sheet.json"
SOURCE_D097 = BASE / "HA_TWO_FLOOR_ATTIC_PRIMARY_BEND_FITTINGS_097" / "attic_primary_bend_fittings.json"
CLAUDE_RESULT = Path(r"C:\Users\zahar\AppData\Local\HomeAuraMultiAgent\results\HA-D113-CLAUDE-RESEARCH-20260813A.json")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(raw).hexdigest().upper()


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D113 is append-only")

    d109 = json.loads(SOURCE_D109.read_text(encoding="utf8"))
    d112 = json.loads(SOURCE_D112.read_text(encoding="utf8"))
    d097 = json.loads(SOURCE_D097.read_text(encoding="utf8"))
    claude = json.loads(CLAUDE_RESULT.read_text(encoding="utf8"))

    model = {
        "schema": "homeaura-floor-primary-research-register-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR_PRIMARY_RESEARCH_113",
        "status": "PRIMARY_SOURCE_RESEARCH_PASS_EXTERNAL_MODEL_CHANNELS_TERMINAL_NO_USABLE_RESPONSE",
        "source_records": [
            {"artifact_id": d109["artifact_id"], "sha256": sha(SOURCE_D109)},
            {"artifact_id": d112["artifact_id"], "sha256": sha(SOURCE_D112)},
            {"artifact_id": d097["artifact_id"], "sha256": sha(SOURCE_D097)},
        ],
        "external_model_channels": {
            "claude": {
                "task_id": claude["task_id"],
                "status": claude["status"],
                "timed_out": claude["timed_out"],
                "duration_ms": claude["duration_ms"],
                "stdout_bytes": claude["stdout_bytes"],
                "stderr_bytes": claude["stderr_bytes"],
                "usable_engineering_response": False,
                "terminal_no_retry_same_request": True,
            },
            "kimi_api": {
                "requested_model": "k3",
                "transport": "HOMEAURA_CANONICAL_CHILD_BROKER",
                "status": "NOT_SENT_PROVIDER_BINDING_UNAVAILABLE",
                "safe_error_code": "OWNER_PROVIDER_BINDING_REQUIRED",
                "canonical_ledger_row_created": False,
                "charged_tokens": 0,
                "usable_engineering_response": False,
                "credentials_or_secrets_persisted": False,
                "terminal_no_retry_same_request": True,
            },
            "model_only_claim_used_for_design": False,
        },
        "official_source_findings": [
            {
                "id": "UPONOR_MLC_1119966",
                "title": "Uponor MLC tap water and heating — Technical information",
                "url": "https://www.uponor.com/getmedia/8677118b-0315-4f8b-a3f4-daf9bb2d346f/mlc-ukpdf?sitename=Estonia",
                "facts": [
                    "32x3_MIN_BEND_RADIUS_WITHOUT_TOOL_160MM",
                    "32x3_MIN_BEND_RADIUS_WITH_UPONOR_TOOL_80MM",
                    "HOT_BENDING_PROHIBITED",
                    "REPEATED_BENDING_AT_SAME_POINT_PROHIBITED",
                    "PIPE_THROUGH_CEILING_OR_WALL_OPENING_MUST_NOT_BEND_OVER_EDGE",
                    "FLOW_OPTIMISED_ELBOW_RECOMMENDED_WHEN_RADIUS_CANNOT_BE_MET",
                ],
                "design_disposition": "D097_ACCESSIBLE_32X32_PRESS_ELBOW_POLICY_RETAINED",
            },
            {
                "id": "UPONOR_TECTO_1141644",
                "title": "Uponor Tecto underfloor heating/cooling — Technical information",
                "url": "https://brandportal.uponor.com/m/2690ed9abceca217/original/TI-Tecto-UFH-C-EN-1141644-v1.pdf",
                "facts": [
                    "COMFORT_PIPE_PLUS_16X2_SUPPORTED_BEND_RADIUS_80MM",
                    "COMFORT_PIPE_PLUS_16X2_FREE_HAND_BEND_RADIUS_128MM",
                    "35MM_SCREED_COVER_IS_SYSTEM_SPECIFIC_NOT_GENERIC",
                ],
                "design_disposition": "OWNER_R80_ACCEPTABLE_ONLY_AS_SUPPORTED_BEND_DESIGN_BASIS_AND_LOOP_SYSTEM_REMAINS_PRODUCT_DEPENDENT",
            },
            {
                "id": "KINGSPAN_TF70_BBA",
                "title": "Kingspan Thermafloor TF70 BBA Certificate",
                "url": "https://www.kingspan.com/content/dam/kingspan/kil/products/thermafloor-tf70-gb-and-ireland/kingspan-thermafloor-tf70-certification-label-bba-en-gb.pdf",
                "facts": [
                    "SERVICES_IN_FLOOR_DUCT_MUST_BE_FIXED_TO_FLOOR_BASE_NOT_INSULATION",
                    "ACCESS_DUCT_SUPPORT_USES_MECHANICALLY_FIXED_BEARERS",
                    "DUCT_SHOULD_BE_AS_NARROW_AS_POSSIBLE_AND_NOT_EXCEED_400MM_FOR_THE_REFERENCED_OVERLAY_CASE",
                    "HOT_PIPE_AIR_SPACE_AND_ACTUAL_FLOOR_SYSTEM_DETAIL_REQUIRE_PRODUCT_CONFIRMATION",
                ],
                "design_disposition": "D109_THIRTY_MM_INSULATION_ALONE_REJECTED_AS_LOAD_BEARING_PROOF",
            },
            {
                "id": "ROCKWOOL_FIREPRO_COLLAR",
                "title": "ROCKWOOL FirePro Pipe Collar",
                "url": "https://www.rockwool.com/uk/products/firepro-pipe-collar/",
                "facts": [
                    "TESTED_PENETRATION_SEALS_ARE_APPLICATION_SPECIFIC",
                    "COMPOSITE_PIPE_AND_RIGID_FLOOR_APPLICATIONS_EXIST",
                    "PRODUCT_SELECTION_REQUIRES_SUBSTRATE_PIPE_OUTER_DIAMETER_AND_RATING",
                ],
                "design_disposition": "NO_FIRESTOP_PRODUCT_SELECTED_UNTIL_REQUIRED_RATING_AND_OPENING_BUILDUP_ARE_KNOWN",
            },
        ],
        "engineering_corrections": [
            {
                "severity": "P0",
                "finding": "THIRTY_MM_INSULATION_ABOVE_TWO_PRIMARIES_IS_THERMAL_INFILL_NOT_A_PROVEN_LOAD_PATH",
                "required_action": "SELECT_AND_CALCULATE_LOAD_BEARING_SERVICE_DUCT_OR_BRIDGE_TO_CARRY_SCREED_FINISH_AND_DESIGN_LOAD",
            },
            {
                "severity": "P0",
                "finding": "PRIMARY_PIPE_SUPPORT_GEOMETRY_WITHIN_SEVENTY_MM_LOWER_ZONE_IS_NOT_SELECTED",
                "required_action": "DESIGN_PRODUCT_COMPATIBLE_SLAB_FIXED_SADDLES_OR_CRADLES_WITHOUT_CRUSHING_FACTORY_INSULATION_AND_RECHECK_HEIGHT",
            },
            {
                "severity": "P0",
                "finding": "SLAB_OPENING_120X200_HAS_NO_STRUCTURAL_OR_PENETRATION_SEAL_RELEASE",
                "required_action": "SCAN_AND_RELEASE_STRUCTURE_THEN_SELECT_SLEEVES_EDGE_PROTECTION_AND_APPLICATION_SPECIFIC_SEAL",
            },
            {
                "severity": "P1",
                "finding": "NO_PIPE_MAY_BE_BENT_OVER_A_CONCRETE_OR_WALL_EDGE",
                "required_action": "USE_SMOOTH_SLEEVES_AND_ACCESSIBLE_DIRECTION_CHANGES; RETAIN_D097_PRESS_ELBOW_POLICY",
            },
            {
                "severity": "P1",
                "finding": "THIRTY_FIVE_MM_COVER_IS_NOT_A_GENERIC_SCREED_APPROVAL",
                "required_action": "SELECT_COMPLETE_UFH_AND_SCREED_SYSTEM_FOR_ACTUAL_LOAD_FINISH_AND_REINFORCEMENT",
            },
            {
                "severity": "P1",
                "finding": "HEATING_ONLY_ASSUMPTION_MUST_BE_EXPLICIT",
                "required_action": "PROHIBIT_COOLING_MODE_UNTIL_VAPOUR_TIGHT_INSULATION_AND_CONDENSATION_ANALYSIS_ARE PROVIDED",
            },
        ],
        "accepted_now": [
            "INTERNAL_ROUTE_NOT_EXTERNAL_WALL",
            "TWO_CONTINUOUS_FACTORY_INSULATED_32X3_PRIMARIES",
            "NO_HIDDEN_FITTINGS",
            "D097_ACCESSIBLE_PRESS_ELBOWS_FOR_DIRECTION_CHANGES",
            "D109_PLAN_AND_3D_NONCONTACT_GEOMETRY_RETAINED_AS_COORDINATION_ONLY",
            "LOOP_PIPE_16X2_R80_ONLY_WITH_SUPPORTED_BENDING_METHOD",
        ],
        "construction_authorized": False,
        "approved_pipe_geometry_count": 0,
        "result": "PASS_RESEARCH_AND_CORRECTION_REGISTER_REWORK_STRUCTURAL_DUCT_PIPE_SUPPORT_AND_PENETRATION_RELEASE",
    }
    model["research_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "floor_primary_research.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf8")
    (OUTPUT / "report.md").write_text(
        "# D113 — проверка узла по официальным источникам\n\n"
        "Claude завершил безопасный read-only запуск по тайм-ауту без вывода. Запрос Kimi API не был отправлен: выделенная пара API key/base URL отсутствует, запись в журнале токенов не создана. Ни одно модельное утверждение не вошло в проект.\n\n"
        "Главная поправка: 30 мм теплоизоляции над двумя магистралями нельзя считать несущим перекрытием канала. Нужен рассчитанный жёсткий мост или сервисный короб, передающий нагрузку на основание/опоры. Сами магистрали должны быть закреплены к плите совместимыми опорами без смятия заводской изоляции; схема опор пока не выбрана.\n\n"
        "Uponor подтверждает для 32×3 минимальный радиус 160 мм без инструмента и 80 мм фирменным инструментом, запрещает горячую и повторную гибку и запрещает перегибать трубу через кромки отверстий. Поэтому сохраняется D097: изменения направления — доступные пресс-отводы, в скрытом канале соединений нет. Для петли 16×2 R80 допустим только как поддерживаемая гибка в рамках выбранной системы; 35 мм стяжки над трубой также остаются системной, а не универсальной величиной.\n\n"
        "Отверстие 120×200 не выпускается до сканирования плиты, решения конструктора, выбора гильз/защиты кромок и конкретного узла заделки. Огнезащитную манжету нельзя назначить по одному диаметру — нужны требуемый предел огнестойкости, конструкция перекрытия и точный наружный габарит проходящих изолированных труб.\n",
        encoding="utf8",
    )
    files = [p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps(
            {
                "artifact_id": model["artifact_id"],
                "research_digest": model["research_digest"],
                "append_only": True,
                "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf8",
    )
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "digest": model["research_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
