from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TMP = ROOT / "tmp"
PROPOSALS = ROOT / "homeaura-native-editor/examples/proposals"

ARTIFACT_ID = "HA_TWO_FLOOR_ATTIC_VERIFIED_PHYSICAL_INPUT_GATE_186"
SOURCE_ARTIFACT_ID = "HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185"
BLOCKED_REASON = "BLOCKED_VERIFIED_ATTIC_ARCHITECTURE_AND_INTERFLOOR_OPENING_INPUTS"
OFFICIAL_STATE = "OFFICIAL_EVIDENCE_ONLY_PHYSICAL_INPUT_GATE_D186"
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)

SCAFFOLD = TMP / "D186_scaffold"
SCAFFOLD_PACKAGE = TMP / f"{ARTIFACT_ID}_SCAFFOLD.zip"
AUDIT_RECEIPT = TMP / "D186_publication_audit_receipt.json"
STAGE = TMP / "D186_official_stage"
STAGE_PACKAGE = TMP / f"{ARTIFACT_ID}_OFFICIAL_STAGE.zip"
OFFICIAL = PROPOSALS / ARTIFACT_ID
OFFICIAL_PACKAGE = PROPOSALS / "packages" / f"{ARTIFACT_ID}.zip"
VALIDATOR = ROOT / "homeaura-native-editor-tests/AtticVerifiedPhysicalInputGate186Validation.cs"
PROGRAM = ROOT / "homeaura-native-editor-tests/Program.cs"

SOURCE_DIRECTORY = PROPOSALS / SOURCE_ARTIFACT_ID
SOURCE_PROJECT = SOURCE_DIRECTORY / "HomeAura_TwoFloor_C12BoundedTerminal_D185.homeaura.json"
SOURCE_CONTRACT = SOURCE_DIRECTORY / "floor1_c12_bounded_terminal_contract.json"
SOURCE_DIAGNOSTICS = SOURCE_DIRECTORY / "engineering_diagnostics.json"
SOURCE_MANIFEST = SOURCE_DIRECTORY / "artifact_manifest.json"
SOURCE_PACKAGE = PROPOSALS / "packages" / f"{SOURCE_ARTIFACT_ID}.zip"

ACCEPTED_SCAFFOLD_PACKAGE_SHA = "B370CB555EEEC2E7041D9C0B4AA5E80D4CD048A67A30023CFCA863CCE5F85ED3"
ACCEPTED_PAYLOAD_HASHES = {
    "README.md": "29EFC168207F52E97E25F78514D8AB6F083A7E65149468918B6734DB48C5D27E",
    "artifact_manifest.json": "32DA87F5ABBB0C905E5564830985A0CD09532B303BA0F60D0625B19AFF8AF019",
    "attic_as_built_input_template.json": "493EC1560FC4CE77F305571911666E1C462778CCB4CF8B3AAC89483A569F7CBF",
    "attic_verified_physical_input_gate.json": "19631431A7A53830F52B40ABF7CD535114B1BE7381B1305FBFF2BC0556B38313",
    "status.json": "5BE1CC30095087EEA16B11870BE11040730A5ED8F242A3223A00EB35E6051F69",
}
AUDIT_RECEIPT_SHA = "53D7DE82A5D31DEAB614FFF205C616187831C01530D0DA565C245E9E1A65CBDA"
VALIDATOR_SHA = "4CBE927D7255ACFF692F8E1F762E3B09B14F033D466D675F95B00434C943B1D3"
PROGRAM_SHA = "0F27CFB69D55E5AAB964FC9572EA5A2C85572CF7461DAA5AE10DEC99EFB2BFCD"
D185_HASHES = {
    SOURCE_PROJECT: "558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4",
    SOURCE_CONTRACT: "4C794B3F632C00DF790F743FECBA488DA378C69A5CBED988A34EB3DF4B4CC726",
    SOURCE_DIAGNOSTICS: "FBC6BEDDECE6828102D4AAAA951B0FB20CAE7E13AE845391667CCCFC377A43B9",
    SOURCE_MANIFEST: "0D4EDA2C54B63D3D7DE69F67D4310CBBEB14C11CA7687814CF7D9EAF6DA57347",
    SOURCE_PACKAGE: "A2B1F9D5DE8171B0546D00CBDA29F9902EB47AC276F27616942FACD00E58DB99",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def deterministic_zip(directory: Path, package: Path) -> None:
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in directory.iterdir() if item.is_file()):
            info = zipfile.ZipInfo(path.name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def require_hash(path: Path, expected: str, label: str) -> None:
    actual = sha(path) if path.is_file() else None
    if actual != expected:
        raise RuntimeError({"D186_publication_input_changed": {
            "label": label, "path": relative(path), "actual": actual, "expected": expected,
        }})


def validate_formal_go_records(receipt: dict) -> None:
    expected = {
        "d186_semantic_audit": "/root/d186_semantic_audit",
        "d186_package_audit": "/root/d186_package_audit",
    }
    records = receipt.get("formal_GO_records")
    if not isinstance(records, list) or len(records) != 2:
        raise RuntimeError("D186 publication requires exactly two formal GO records")
    auditor_ids = [record.get("auditor_id") for record in records]
    if len(set(auditor_ids)) != 2 or set(auditor_ids) != set(expected):
        raise RuntimeError("D186 formal GO records are not exact and unique")
    for record in records:
        auditor = record["auditor_id"]
        if record.get("canonical_agent_path") != expected[auditor] or \
                record.get("verdict") != "FORMAL GO" or \
                record.get("accepted_scaffold_package_sha256") != ACCEPTED_SCAFFOLD_PACKAGE_SHA or \
                record.get("P1_count") != 0 or record.get("P2_count") != 0 or \
                not str(record.get("go_record_id", "")).startswith(f"{auditor}_FORMAL_GO_"):
            raise RuntimeError(f"D186 formal GO record changed: {auditor}")


def validate_inputs() -> tuple[dict, dict, dict]:
    require_hash(SCAFFOLD_PACKAGE, ACCEPTED_SCAFFOLD_PACKAGE_SHA, "accepted scaffold package")
    for name, expected in ACCEPTED_PAYLOAD_HASHES.items():
        require_hash(SCAFFOLD / name, expected, f"accepted scaffold payload {name}")
    require_hash(AUDIT_RECEIPT, AUDIT_RECEIPT_SHA, "publication audit receipt")
    require_hash(VALIDATOR, VALIDATOR_SHA, "final dual-mode D186 validator")
    require_hash(PROGRAM, PROGRAM_SHA, "post-registration Program")
    for path, expected in D185_HASHES.items():
        require_hash(path, expected, f"immutable D185 {path.name}")

    expected_names = [
        "artifact_manifest.json", "attic_as_built_input_template.json",
        "attic_verified_physical_input_gate.json", "README.md", "status.json",
    ]
    if sorted((path.name for path in SCAFFOLD.iterdir() if path.is_file()), key=str.casefold) != \
            sorted(expected_names, key=str.casefold):
        raise RuntimeError("Accepted D186 scaffold member set changed")
    with zipfile.ZipFile(SCAFFOLD_PACKAGE, "r") as archive:
        if archive.namelist() != expected_names:
            raise RuntimeError("Accepted D186 scaffold ZIP order/member set changed")
        for entry in archive.infolist():
            if entry.date_time != FIXED_ZIP_TIME or \
                    archive.read(entry.filename) != (SCAFFOLD / entry.filename).read_bytes():
                raise RuntimeError(f"Accepted D186 scaffold ZIP parity changed: {entry.filename}")

    gate = load(SCAFFOLD / "attic_verified_physical_input_gate.json")
    status = load(SCAFFOLD / "status.json")
    receipt = load(AUDIT_RECEIPT)
    if gate.get("publication_state") != "SCAFFOLD_REVIEW_REQUIRED_NOT_OFFICIAL" or \
            gate.get("result") != BLOCKED_REASON or status.get("result") != BLOCKED_REASON:
        raise RuntimeError("Accepted D186 scaffold publication/block state changed")
    if receipt.get("accepted_scaffold_package_sha256") != ACCEPTED_SCAFFOLD_PACKAGE_SHA or \
            receipt.get("required_formal_GO_count") != 2 or \
            receipt.get("received_formal_GO_count") != 2 or \
            receipt.get("explicit_root_GO") is not True or \
            receipt.get("publication_state_authorized") != OFFICIAL_STATE or \
            receipt.get("result_remains") != BLOCKED_REASON:
        raise RuntimeError("D186 audit receipt root/GO/publication binding changed")
    if receipt.get("accepted_scaffold_payload_sha256") != ACCEPTED_PAYLOAD_HASHES:
        raise RuntimeError("D186 audit receipt payload binding changed")
    validate_formal_go_records(receipt)

    capability = gate["native_schema_11_capability_binding"]
    implementation = capability["implementation_files"]
    if len(implementation) != 9 or capability["acceptance_evidence_binding"].get(
            "registered_suite_result") != "RESULT_56_OF_56_PASSED":
        raise RuntimeError("Accepted D186 historical 9-file/56 binding changed")
    for item in implementation:
        path = ROOT / item["path"]
        if item["path"] == "homeaura-native-editor-tests/Program.cs":
            if item["sha256"] != "6EE05E55746AA2F4031D111BAF94D25C1271AB262C327D264F78EC398DE867A0":
                raise RuntimeError("Accepted D186 historical Program binding changed")
        elif sha(path) != item["sha256"]:
            raise RuntimeError(f"D186 current implementation drifted outside Program: {item['path']}")

    contract = load(SOURCE_CONTRACT)
    manifest = load(SOURCE_MANIFEST)
    if contract.get("publication_state") != "OFFICIAL_BOUNDED_TERMINAL_D185" or \
            manifest.get("publication_state") != "OFFICIAL_BOUNDED_TERMINAL_D185":
        raise RuntimeError("D186 publication requires unchanged official D185")
    return gate, status, receipt


def current_implementation_binding(historical_capability: dict) -> list[dict[str, str]]:
    result = json.loads(json.dumps(historical_capability["implementation_files"]))
    for item in result:
        if item["path"] == "homeaura-native-editor-tests/Program.cs":
            item["sha256"] = PROGRAM_SHA
    return result


def accepted_scaffold_binding(historical_capability: dict) -> dict:
    return {
        "accepted_scaffold_package_sha256": ACCEPTED_SCAFFOLD_PACKAGE_SHA,
        "accepted_scaffold_payload_sha256": ACCEPTED_PAYLOAD_HASHES,
        "historical_native_schema_11_capability_binding_digest": digest(historical_capability),
        "historical_registered_suite_result": "RESULT_56_OF_56_PASSED",
        "historical_registered_suite_program_sha256":
            "6EE05E55746AA2F4031D111BAF94D25C1271AB262C327D264F78EC398DE867A0",
    }


def official_publication_summary(receipt: dict) -> dict:
    return {
        "publication_state": OFFICIAL_STATE,
        "accepted_scaffold_package_sha256": ACCEPTED_SCAFFOLD_PACKAGE_SHA,
        "audit_receipt_path": "publication_audit_receipt.json",
        "audit_receipt_sha256": AUDIT_RECEIPT_SHA,
        "required_formal_GO_count": 2,
        "received_formal_GO_count": 2,
        "formal_GO_records": receipt["formal_GO_records"],
        "explicit_root_GO": True,
        "independent_reviewer_GO_received": True,
        "official_freeze_allowed": True,
        "root_review_required": False,
        "physical_release_allowed": False,
        "installation_allowed": False,
    }


def current_official_binding(historical_capability: dict) -> dict:
    implementation = current_implementation_binding(historical_capability)
    return {
        "runtime_test_doc_surface_file_count": len(implementation),
        "implementation_files": implementation,
        "surface_binding_digest": digest(implementation),
        "release_build_result": "PASS_0_WARNINGS_0_ERRORS",
        "registered_suite_result": "RESULT_57_OF_57_PASSED",
        "registered_suite_program_path": relative(PROGRAM),
        "registered_suite_program_sha256": PROGRAM_SHA,
        "direct_validator_path": relative(VALIDATOR),
        "direct_validator_sha256": VALIDATOR_SHA,
        "direct_D186_validator_result": "PASS",
        "accepted_scaffold_package_sha256": ACCEPTED_SCAFFOLD_PACKAGE_SHA,
        "publication_audit_receipt_sha256": AUDIT_RECEIPT_SHA,
    }


def build_payload(directory: Path) -> None:
    accepted_gate, accepted_status, receipt = validate_inputs()
    historical_capability = accepted_gate["native_schema_11_capability_binding"]
    accepted_binding = accepted_scaffold_binding(historical_capability)
    publication = official_publication_summary(receipt)
    current_binding = current_official_binding(historical_capability)

    shutil.copyfile(SCAFFOLD / "attic_as_built_input_template.json",
                    directory / "attic_as_built_input_template.json")
    shutil.copyfile(AUDIT_RECEIPT, directory / "publication_audit_receipt.json")

    gate = json.loads(json.dumps(accepted_gate))
    gate["publication_state"] = OFFICIAL_STATE
    gate["release_boundary"]["official_D186_freeze_allowed"] = True
    gate["release_boundary"]["root_review_required"] = False
    gate["release_boundary"]["independent_D186_package_reviewer_GO_received"] = True
    gate["accepted_scaffold_validation_binding"] = accepted_binding
    gate["official_publication"] = publication
    gate["current_official_validation_binding"] = current_binding
    gate.pop("gate_digest", None)
    gate["gate_digest"] = digest(gate)
    dump(directory / "attic_verified_physical_input_gate.json", gate)

    status = json.loads(json.dumps(accepted_status))
    status["publication_state"] = OFFICIAL_STATE
    status["publishable"] = False
    status["official_files_modified"] = True
    status["root_review_required"] = False
    status["independent_D186_package_reviewer_GO_received"] = True
    status["official_D186_freeze_allowed"] = True
    status["historical_native_schema_11_capability_binding"] = historical_capability
    status["accepted_scaffold_validation_binding"] = accepted_binding
    status["official_publication"] = publication
    status["current_official_validation_binding"] = current_binding
    dump(directory / "status.json", status)

    accepted_readme = (SCAFFOLD / "README.md").read_text(encoding="utf-8")
    accepted_readme = accepted_readme.replace(
        "# D186 scaffold · verified physical input gate мансарды",
        "# Official D186 · evidence-only verified physical input gate мансарды",
        1,
    )
    accepted_readme = accepted_readme.replace(
        "Official freeze и регистрация теста заблокированы до независимого D186 package reviewer GO и root review.",
        "На accepted-scaffold этапе official freeze и регистрация были заблокированы до D186 package reviewer GO и root review; оба условия теперь доказаны receipt и explicit root GO без изменения physical release gates.",
    )
    readme = accepted_readme + (
        "\n## Official evidence-only publication\n\n"
        f"Publication state: `{OFFICIAL_STATE}`. Exact accepted scaffold ZIP: "
        f"`{ACCEPTED_SCAFFOLD_PACKAGE_SHA}`. Audit receipt: `{AUDIT_RECEIPT_SHA}`. "
        "Unique `d186_semantic_audit` and `d186_package_audit` records both say `FORMAL GO` for that "
        "same SHA, and explicit root GO is true.\n\n"
        f"Current validation binding: `RESULT_57_OF_57_PASSED`, Program `{PROGRAM_SHA}`, direct D186 "
        f"validator `PASS` at `{VALIDATOR_SHA}`. The accepted-scaffold 9-file/56 block remains historical "
        "evidence and is not rewritten.\n\n"
        "This is no geometry, routes, sleeves, `.homeaura`, renders or installation claim. Result and "
        f"blocked_reason remain `{BLOCKED_REASON}`; every physical, routing, structural, K2/owner-style, "
        "install and installation-ready release remains false.\n"
    )
    (directory / "README.md").write_text(readme, encoding="utf-8")

    guard = {
        "active": False,
        "evidence_only_official_publication_allowed": True,
        "independent_reviewer_GO_received": True,
        "explicit_root_GO_received": True,
        "official_freeze_allowed": True,
        "root_review_required": False,
        "physical_release_allowed": False,
        "installation_allowed": False,
    }
    payloads = sorted(path for path in directory.iterdir()
                      if path.is_file() and path.name != "artifact_manifest.json")
    manifest = {
        "artifact_id": ARTIFACT_ID,
        "append_only": True,
        "evidence_only": True,
        "publication_state": OFFICIAL_STATE,
        "result": BLOCKED_REASON,
        "blocked_reason": BLOCKED_REASON,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_project_sha256": D185_HASHES[SOURCE_PROJECT],
        "source_contract_sha256": D185_HASHES[SOURCE_CONTRACT],
        "source_diagnostics_sha256": D185_HASHES[SOURCE_DIAGNOSTICS],
        "source_manifest_sha256": D185_HASHES[SOURCE_MANIFEST],
        "source_package_sha256": D185_HASHES[SOURCE_PACKAGE],
        "official_publisher": {"path": relative(Path(__file__)), "sha256": sha(Path(__file__))},
        "official_validator": {"path": relative(VALIDATOR), "sha256": VALIDATOR_SHA},
        "registered_suite_program": {"path": relative(PROGRAM), "sha256": PROGRAM_SHA},
        "publication_audit_receipt": {
            "path": "publication_audit_receipt.json", "sha256": AUDIT_RECEIPT_SHA,
        },
        "historical_native_schema_11_capability_binding": historical_capability,
        "accepted_scaffold_validation_binding": accepted_binding,
        "official_publication": publication,
        "current_official_validation_binding": current_binding,
        "publication_guard": guard,
        "zip_contract": {
            "member_order": "LEXICOGRAPHIC_FILENAME",
            "timestamp": "1980-01-01T00:00:00",
            "compression": "DEFLATE_LEVEL_9",
            "directory_prefix": False,
        },
        "publishable": False,
        "installation_ready": False,
        "install": False,
        "homeaura_file_count": 0,
        "render_file_count": 0,
        "geometry_file_count": 0,
        "route_file_count": 0,
        "sleeve_file_count": 0,
        "files": [
            {"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)}
            for path in payloads
        ],
    }
    dump(directory / "artifact_manifest.json", manifest)


def compare_directories(expected: Path, actual: Path, label: str) -> None:
    expected_names = sorted(path.name for path in expected.iterdir() if path.is_file())
    actual_names = sorted(path.name for path in actual.iterdir() if path.is_file())
    if actual_names != expected_names:
        raise RuntimeError(f"{label} member set differs: expected {expected_names}, actual {actual_names}")
    for name in expected_names:
        if (expected / name).read_bytes() != (actual / name).read_bytes():
            raise RuntimeError(f"{label} byte parity failed: {name}")


def build_candidate(temporary: Path) -> tuple[Path, Path]:
    directory = temporary / ARTIFACT_ID
    directory.mkdir()
    build_payload(directory)
    package = temporary / STAGE_PACKAGE.name
    deterministic_zip(directory, package)
    return directory, package


def safe_refresh_stage() -> None:
    expected_stage = (ROOT / "tmp/D186_official_stage").resolve()
    expected_package = (ROOT / f"tmp/{ARTIFACT_ID}_OFFICIAL_STAGE.zip").resolve()
    if STAGE.resolve() != expected_stage or STAGE_PACKAGE.resolve() != expected_package:
        raise RuntimeError("Unsafe D186 fixed stage refresh target")
    if STAGE.exists():
        if not STAGE.is_dir():
            raise RuntimeError("D186 fixed stage target is not a directory")
        shutil.rmtree(STAGE)
    if STAGE_PACKAGE.exists():
        if not STAGE_PACKAGE.is_file():
            raise RuntimeError("D186 fixed stage package target is not a file")
        STAGE_PACKAGE.unlink()


def prepare_stage(refresh: bool) -> str:
    validate_inputs()
    if STAGE.exists() != STAGE_PACKAGE.exists():
        if not refresh:
            raise FileExistsError("D186 fixed official stage is partial; exact refresh flag required")
        safe_refresh_stage()
    with tempfile.TemporaryDirectory(prefix="D186_official_candidate_", dir=TMP) as temporary_name:
        candidate, candidate_package = build_candidate(Path(temporary_name))
        if STAGE.exists():
            if refresh:
                safe_refresh_stage()
            else:
                compare_directories(candidate, STAGE, "D186 deterministic fixed stage")
                if candidate_package.read_bytes() != STAGE_PACKAGE.read_bytes():
                    raise RuntimeError("D186 deterministic fixed stage ZIP parity failed")
                return "DETERMINISTIC_STAGE_PARITY_PASS_UNCHANGED"
        shutil.move(str(candidate), str(STAGE))
        shutil.move(str(candidate_package), str(STAGE_PACKAGE))
    return "CREATED_FIXED_TMP_OFFICIAL_STAGE"


def validate_stage_against_fresh_candidate() -> None:
    if not STAGE.is_dir() or not STAGE_PACKAGE.is_file():
        raise FileNotFoundError("D186 fixed official stage/package is absent")
    with tempfile.TemporaryDirectory(prefix="D186_official_replay_", dir=TMP) as temporary_name:
        candidate, candidate_package = build_candidate(Path(temporary_name))
        compare_directories(candidate, STAGE, "D186 fixed stage replay")
        if candidate_package.read_bytes() != STAGE_PACKAGE.read_bytes():
            raise RuntimeError("D186 fixed stage ZIP replay parity failed")


def publish_official() -> str:
    validate_stage_against_fresh_candidate()
    official_exists = OFFICIAL.exists()
    package_exists = OFFICIAL_PACKAGE.exists()
    if official_exists != package_exists:
        raise FileExistsError("D186 official publication is partial; refusing repair or overwrite")
    if official_exists:
        if not OFFICIAL.is_dir() or not OFFICIAL_PACKAGE.is_file():
            raise FileExistsError("D186 official targets have unexpected types")
        compare_directories(STAGE, OFFICIAL, "D186 official replay")
        if STAGE_PACKAGE.read_bytes() != OFFICIAL_PACKAGE.read_bytes():
            raise RuntimeError("D186 official ZIP replay parity failed")
        return "OFFICIAL_REPLAY_PARITY_PASS_NO_OVERWRITE"

    OFFICIAL.parent.mkdir(parents=True, exist_ok=True)
    OFFICIAL_PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(STAGE, OFFICIAL)
    shutil.copyfile(STAGE_PACKAGE, OFFICIAL_PACKAGE)
    compare_directories(STAGE, OFFICIAL, "D186 newly published official directory")
    if STAGE_PACKAGE.read_bytes() != OFFICIAL_PACKAGE.read_bytes():
        raise RuntimeError("D186 newly published official ZIP is not byte-identical to fixed stage")
    return "PUBLISHED_EXACT_VALIDATED_STAGE_BYTES"


def main() -> None:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare-stage", action="store_true")
    action.add_argument("--publish-official", action="store_true")
    parser.add_argument("--explicit-root-go", action="store_true")
    parser.add_argument("--refresh-stage", action="store_true")
    parser.add_argument("--validated-release-57", action="store_true")
    parser.add_argument("--direct-d186-pass", action="store_true")
    args = parser.parse_args()
    if not args.explicit_root_go:
        raise RuntimeError("D186 official staging/publication requires explicit root GO")
    if args.publish_official and (not args.validated_release_57 or not args.direct_d186_pass):
        raise RuntimeError("D186 publish requires staged Release57 and direct-D186 PASS flags")
    if args.refresh_stage and not args.prepare_stage:
        raise RuntimeError("D186 --refresh-stage is bounded to --prepare-stage")

    result = prepare_stage(args.refresh_stage) if args.prepare_stage else publish_official()
    print(json.dumps({
        "artifact_id": ARTIFACT_ID,
        "action": result,
        "publication_state": OFFICIAL_STATE,
        "result": BLOCKED_REASON,
        "stage_directory": str(STAGE),
        "stage_package": str(STAGE_PACKAGE),
        "stage_manifest_sha256": sha(STAGE / "artifact_manifest.json"),
        "stage_package_sha256": sha(STAGE_PACKAGE),
        "official_directory": str(OFFICIAL) if OFFICIAL.exists() else None,
        "official_package": str(OFFICIAL_PACKAGE) if OFFICIAL_PACKAGE.exists() else None,
        "official_manifest_sha256": sha(OFFICIAL / "artifact_manifest.json") if OFFICIAL.exists() else None,
        "official_package_sha256": sha(OFFICIAL_PACKAGE) if OFFICIAL_PACKAGE.exists() else None,
        "publisher_sha256": sha(Path(__file__)),
        "validator_sha256": VALIDATOR_SHA,
        "Program_sha256": PROGRAM_SHA,
        "accepted_scaffold_package_sha256": ACCEPTED_SCAFFOLD_PACKAGE_SHA,
        "publication_audit_receipt_sha256": AUDIT_RECEIPT_SHA,
        "explicit_root_GO": True,
        "added_geometry_count": 0,
        "homeaura_file_count": 0,
        "render_file_count": 0,
        "route_file_count": 0,
        "sleeve_file_count": 0,
        "installation_ready": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
