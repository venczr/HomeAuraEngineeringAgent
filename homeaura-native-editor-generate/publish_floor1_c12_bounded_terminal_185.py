from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCAFFOLD = ROOT / "tmp/D185_scaffold"
SCAFFOLD_PACKAGE = ROOT / "tmp/HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185_SCAFFOLD.zip"
SCAFFOLD_VALIDATION = ROOT / "tmp/D185_scaffold_validation.json"
OFFICIAL = ROOT / (
    "homeaura-native-editor/examples/proposals/"
    "HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185"
)
OFFICIAL_PACKAGE = ROOT / (
    "homeaura-native-editor/examples/proposals/packages/"
    "HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185.zip"
)
HERMETIC_TEST = ROOT / "homeaura-native-editor-tests/C12BoundedTerminal185Validation.cs"
PROJECT_NAME = "HomeAura_TwoFloor_C12BoundedTerminal_D185.homeaura.json"
CONTRACT_NAME = "floor1_c12_bounded_terminal_contract.json"
REPORT_NAME = "floor1_c12_bounded_terminal_report.json"
ARTIFACT_ID = "HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185"
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)

EXPECTED = {
    SCAFFOLD_PACKAGE: "EB6A27C3773166CEFAA072E5C6E293AB24BFE5FB1A00B89EFDDD662B7E7A5CDA",
    SCAFFOLD_VALIDATION: "5ACA69C96A2A4EAE9503F68ACF3721C1B9F9D1D66116537CA1311363F7B2F533",
    SCAFFOLD / PROJECT_NAME: "558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4",
    SCAFFOLD / "engineering_diagnostics.json": "FBC6BEDDECE6828102D4AAAA951B0FB20CAE7E13AE845391667CCCFC377A43B9",
    SCAFFOLD / "artifact_manifest.json": "22C3045E8B2CC4755876A1567EA754B63E825D32F673DE31FC5980F9B5589203",
    SCAFFOLD / "render_provenance.json": "72C782B98E8463272D3718BF84EC3D62F3AE873AAA033F5C8FD2CF8321911728",
    HERMETIC_TEST: "2414E57264DBD83388774E75206F8178732358919AD7B84B10A06BCC6B2B3386",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_scaffold_package() -> None:
    for path, expected in EXPECTED.items():
        if not path.is_file() or sha(path) != expected:
            raise RuntimeError({"D185_publication_input_changed": {
                "path": str(path), "actual": sha(path) if path.is_file() else None, "expected": expected,
            }})
    validation = load(SCAFFOLD_VALIDATION)
    if not validation.get("all_scaffold_validation_gates_pass") or \
            not validation.get("publication_guard_remains_active"):
        raise RuntimeError("D185 accepted scaffold validation is not exact PASS with its prepublication guard")
    with zipfile.ZipFile(SCAFFOLD_PACKAGE, "r") as archive:
        expected_names = sorted(path.name for path in SCAFFOLD.iterdir() if path.is_file())
        if sorted(archive.namelist()) != expected_names:
            raise RuntimeError("D185 accepted scaffold ZIP member set changed")
        for entry in archive.infolist():
            if entry.date_time != FIXED_ZIP_TIME or archive.read(entry.filename) != (SCAFFOLD / entry.filename).read_bytes():
                raise RuntimeError(f"D185 accepted scaffold ZIP parity changed: {entry.filename}")


def deterministic_zip(directory: Path, package: Path) -> None:
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in directory.iterdir() if item.is_file()):
            info = zipfile.ZipInfo(path.name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def safe_refresh() -> None:
    expected_official = (ROOT / (
        "homeaura-native-editor/examples/proposals/"
        "HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185"
    )).resolve()
    expected_package = (ROOT / (
        "homeaura-native-editor/examples/proposals/packages/"
        "HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185.zip"
    )).resolve()
    if OFFICIAL.resolve() != expected_official or OFFICIAL_PACKAGE.resolve() != expected_package:
        raise RuntimeError("Unsafe D185 official refresh target")
    if OFFICIAL.exists():
        shutil.rmtree(OFFICIAL)
    if OFFICIAL_PACKAGE.exists():
        OFFICIAL_PACKAGE.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish-bounded-terminal", action="store_true")
    parser.add_argument("--explicit-root-go", action="store_true")
    parser.add_argument("--refresh-official", action="store_true")
    args = parser.parse_args()
    if not args.publish_bounded_terminal or not args.explicit_root_go:
        raise RuntimeError("D185 official publication requires bounded-terminal scope and explicit root GO flags")
    if OFFICIAL.exists() or OFFICIAL_PACKAGE.exists():
        if not args.refresh_official:
            raise FileExistsError("D185 official artifact exists; use --refresh-official only for the exact official targets")
        safe_refresh()

    validate_scaffold_package()
    OFFICIAL.mkdir(parents=True)
    OFFICIAL_PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    for path in SCAFFOLD.iterdir():
        if path.is_file() and path.name not in {CONTRACT_NAME, REPORT_NAME, "status.json", "README.md", "artifact_manifest.json"}:
            shutil.copyfile(path, OFFICIAL / path.name)

    audit_evidence = {
        "accepted_scaffold_package_sha256": EXPECTED[SCAFFOLD_PACKAGE],
        "accepted_scaffold_validation_sha256": EXPECTED[SCAFFOLD_VALIDATION],
        "required_formal_GO_count": 2,
        "received_formal_GO_count": 2,
        "formal_GO_records": [
            {
                "auditor_id": "/root/c12_domain_design",
                "verdict": "GO_BOUNDED_TERMINAL_SCAFFOLD_V2",
                "package_sha256": EXPECTED[SCAFFOLD_PACKAGE],
                "scope": "bounded-terminal package only; not install-ready, exact-Eurocone, or collector-continuous",
            },
            {
                "auditor_id": "/root/attic_next_boundary",
                "verdict": "GO_BOUNDED_TERMINAL_SCAFFOLD_V2",
                "package_sha256": EXPECTED[SCAFFOLD_PACKAGE],
                "scope": "bounded-terminal package only; not install-ready, exact-Eurocone, or collector-continuous",
            },
        ],
        "explicit_root_GO_received": True,
        "root_GO_basis": "two formal independent GO records for the exact accepted scaffold package",
        "publication_scope": "OFFICIAL_BOUNDED_TERMINAL_ONLY",
        "excluded_claims": ["INSTALLATION_READY", "EXACT_EUROCONE_CONTINUITY", "COLLECTOR_CONTINUOUS", "COMPLETE_K1"],
    }
    official_guard = {
        "active": False,
        "official_publication_allowed": True,
        "Program_registration_allowed": True,
        "official_freeze_allowed": True,
        "native_final_materialized_terminal_ramp_gate": "PASS",
        "independent_GO_required": 2,
        "independent_GO_received": 2,
        "explicit_root_GO_received": True,
        "bounded_terminal_publication_gate": "PASS",
        "installation_publication_allowed": False,
        "exact_Eurocone_continuity_claim_allowed": False,
        "release_condition": "bounded-terminal official publication satisfied; installation and exact-Eurocone claims remain blocked",
    }

    contract = load(SCAFFOLD / CONTRACT_NAME)
    contract["status"] = "OFFICIAL_BOUNDED_TERMINAL_D185"
    contract["publication_state"] = "OFFICIAL_BOUNDED_TERMINAL_D185"
    contract["publication_guard"] = official_guard
    contract["independent_audit_evidence"] = audit_evidence
    contract["source_provenance"]["accepted_scaffold_package"] = {
        "path": str(SCAFFOLD_PACKAGE.relative_to(ROOT)).replace("\\", "/"),
        "sha256": EXPECTED[SCAFFOLD_PACKAGE],
    }
    contract["source_provenance"]["accepted_scaffold_validation"] = {
        "path": str(SCAFFOLD_VALIDATION.relative_to(ROOT)).replace("\\", "/"),
        "sha256": EXPECTED[SCAFFOLD_VALIDATION],
    }
    contract["source_provenance"]["official_publisher"] = {
        "path": str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha(Path(__file__).resolve()),
    }
    contract["source_provenance"]["hermetic_official_validation"] = {
        "path": str(HERMETIC_TEST.relative_to(ROOT)).replace("\\", "/"),
        "sha256": EXPECTED[HERMETIC_TEST],
        "Program_registration_authorized": True,
    }
    contract["next_gate"] = (
        "FOR_EXACT_EUROCONE_OR_INSTALLATION_CLAIMS_SHORTEN_ROUTE_AT_LEAST_765_032MM_"
        "MATERIALIZE_BOTH_TAILS_AND_REPEAT_FULL_3D_AUDIT"
    )

    report = load(SCAFFOLD / REPORT_NAME)
    report["publication_state"] = contract["publication_state"]
    report["publication_guard"] = official_guard
    report["independent_audit_evidence"] = audit_evidence

    status = load(SCAFFOLD / "status.json")
    status["result"] = "OFFICIAL_BOUNDED_TERMINAL_D185_INSTALLATION_CLAIMS_BLOCKED"
    status["publication_state"] = contract["publication_state"]
    status["official_files_modified"] = True
    status["independent_GO_received"] = 2
    status["explicit_root_GO_received"] = True
    status["publication_guard"] = official_guard

    dump(OFFICIAL / CONTRACT_NAME, contract)
    dump(OFFICIAL / REPORT_NAME, report)
    dump(OFFICIAL / "status.json", status)
    readme = (
        "# Official D185 · C12 bounded-terminal Point3\n\n"
        "Это официальный append-only bounded-terminal D185: относительно immutable D184 изменён только "
        "F1-D171-C12; non-circuit payload и остальные 13 circuits сохранены. Project SHA256 — "
        f"`{EXPECTED[SCAFFOLD / PROJECT_NAME]}`; current-Release diagnostics SHA256 — "
        f"`{EXPECTED[SCAFFOLD / 'engineering_diagnostics.json']}`.\n\n"
        "Native materialized-terminal-ramp gate PASS относится только к соседнему TRANSIT S_BEND_R80 segment 31, "
        "который точно завершает W030-L2. Legacy raw/useful/open diagnostics и project Design остаются false; "
        "TRANSIT не превращён в BODY. BODY q128=98.748535%, max=174.558 мм, over200=0; rounded length "
        "72.846950 м; physical/Point3/contact/wall/R80 gates проходят.\n\n"
        "Коллекторная непрерывность не заявлена: collectorContinuous=0, completeK1=0, Eurocone tails deferred. "
        "Сумма прямых нижних границ хвостов 7918.081525 мм даёт минимум 80765.031288 мм, на "
        "765.031288 мм выше 80 м. До exact Eurocone/install claims требуется сократить route минимум на "
        "765.032 мм, материализовать оба хвоста и повторить полный 3D audit. Native completed:true означает "
        "только bounded-terminal completion в пределах K1 tolerance 4100 мм.\n\n"
        "FLOOR_1 содержит 14 LOOP, AXIS=0, concealed=0; K2/ATTIC routes=0; sleeves=0; "
        "installation_ready=false; publishable=false. Оба R01 crop показывают C12 как focus вместе с контекстом "
        "соседних project circuits; full-floor clean ограничен FLOOR_1 без ATTIC overlay.\n\n"
        f"Официальная bounded-terminal публикация основана на двух formal independent GO для scaffold ZIP "
        f"`{EXPECTED[SCAFFOLD_PACKAGE]}` и explicit root GO. Это не разрешение на installation-ready, "
        "collector-continuous или exact-Eurocone claims.\n"
    )
    (OFFICIAL / "README.md").write_text(readme, encoding="utf-8")

    payloads = sorted(path for path in OFFICIAL.iterdir() if path.is_file() and path.name != "artifact_manifest.json")
    manifest = {
        "artifact_id": ARTIFACT_ID,
        "append_only": True,
        "publication_state": contract["publication_state"],
        "project_sha256": EXPECTED[SCAFFOLD / PROJECT_NAME],
        "engineering_diagnostics_sha256": EXPECTED[SCAFFOLD / "engineering_diagnostics.json"],
        "accepted_scaffold_package_sha256": EXPECTED[SCAFFOLD_PACKAGE],
        "official_publisher_sha256": sha(Path(__file__).resolve()),
        "hermetic_validation_source_sha256": EXPECTED[HERMETIC_TEST],
        "publication_guard_active": False,
        "publishable": False,
        "installation_ready": False,
        "files": [
            {"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)}
            for path in payloads
        ],
    }
    dump(OFFICIAL / "artifact_manifest.json", manifest)
    deterministic_zip(OFFICIAL, OFFICIAL_PACKAGE)
    print(json.dumps({
        "artifact_id": ARTIFACT_ID,
        "publication_state": contract["publication_state"],
        "official_directory": str(OFFICIAL),
        "official_package": str(OFFICIAL_PACKAGE),
        "project_sha256": sha(OFFICIAL / PROJECT_NAME),
        "diagnostics_sha256": sha(OFFICIAL / "engineering_diagnostics.json"),
        "manifest_sha256": sha(OFFICIAL / "artifact_manifest.json"),
        "package_sha256": sha(OFFICIAL_PACKAGE),
        "publisher_sha256": sha(Path(__file__).resolve()),
        "audit_evidence": audit_evidence,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
