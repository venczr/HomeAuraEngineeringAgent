from __future__ import annotations

import json
import math
import tempfile
import unittest

from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from agent.domain_adapter import adapt_rooms_payload
from agent.project_foundation import (
    build_canonical_project_preview,
    build_project_seed,
    canonical_json_bytes,
    load_sheet_manifest,
    ProjectFoundationError,
    replace_active_source_point,
    sha256_hex,
    sheet_manifest_reference,
)
from agent.project_models import (
    Assumption,
    AssumptionCriticality,
    AssumptionStatus,
    AuditActorKind,
    AuditEvent,
    CatalogSourceType,
    CatalogSourceVerificationStatus,
    CatalogVerificationStatus,
    CanonicalProjectModel,
    DesignVariantKind,
    DesignVariantMetadata,
    DesignVariantStatus,
    EQUIPMENT_VERIFIABLE_FIELDS,
    EquipmentCatalogSource,
    EquipmentCatalogItem,
    Issue,
    IssueSeverity,
    IssueStatus,
    Point3D,
    ProjectJsonError,
    ProjectLifecycleStatus,
    ProjectSeedStatus,
    SheetManifest,
    SourceEvidenceKind,
    SourcePoint,
    SourcePointEvidence,
    SourcePointKind,
    SourcePointState,
    UnitVector3D,
)


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
ROOMS_FIXTURE = (
    ROOT_DIRECTORY / "tests" / "fixtures" / "rooms_v1_0.json"
)
FIXED_TIME = datetime(
    2026,
    7,
    27,
    8,
    0,
    tzinfo=timezone.utc,
)
BOILER_POINT_ID = UUID(
    "346cceae-69fb-59e5-a2c4-4f96e34431c9"
)
WATER_POINT_ID_V1 = UUID(
    "848f32d1-e459-522f-b0ad-ea8ea81ec8c1"
)
WATER_POINT_ID_V2 = UUID(
    "fb670283-c329-55a9-b3fe-8dd68790e637"
)
MANUFACTURER_IDENTITY_UNSET = object()
PERSISTED_CATALOG_STRINGS = {
    "manufacturer": "  Acme   GmbH  ",
    "brand": "  Bränd   Pro  ",
    "model": " M－42  Plus ",
    "article": " AB-12   34 ",
    "category": " Heat   Pump ",
}


class ProjectFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = json.loads(
            ROOMS_FIXTURE.read_text(encoding="utf-8")
        )
        cls.domain = adapt_rooms_payload(
            payload,
            project_id="project-foundation-test",
        )
        cls.room = (
            cls.domain.project.buildings[0]
            .levels[0]
            .rooms[0]
        )
        cls.level = cls.domain.project.buildings[0].levels[0]

    def boiler_point(
        self,
        *,
        state: SourcePointState = SourcePointState.MARKED,
        evidence_kind: SourceEvidenceKind = (
            SourceEvidenceKind.USER_MARKED
        ),
    ) -> SourcePoint:
        return SourcePoint(
            source_point_id=BOILER_POINT_ID,
            kind=SourcePointKind.BOILER_ROOM,
            revision=1,
            state=state,
            world_coordinates_m=Point3D(
                x_m=1.0,
                y_m=2.0,
                z_m=0.0,
            ),
            local_coordinates_m=Point3D(
                x_m=1.0,
                y_m=2.0,
                z_m=0.0,
            ),
            level_id=self.level.stable_id,
            room_id=self.room.stable_id,
            confidence=1.0,
            evidence=SourcePointEvidence(
                kind=evidence_kind,
                method="closed_room_selection",
                drawing_name=self.domain.project.drawing_name,
                source_handle=self.room.source_handle,
                observed_at=FIXED_TIME,
            ),
        )

    def water_point(
        self,
        *,
        point_id: UUID = WATER_POINT_ID_V1,
        revision: int = 1,
        x_m: float = 4.0,
        state: SourcePointState = SourcePointState.MARKED,
        evidence_kind: SourceEvidenceKind = (
            SourceEvidenceKind.USER_MARKED
        ),
    ) -> SourcePoint:
        return SourcePoint(
            source_point_id=point_id,
            kind=SourcePointKind.WATER_INLET,
            revision=revision,
            state=state,
            world_coordinates_m=Point3D(
                x_m=x_m,
                y_m=5.0,
                z_m=0.2,
            ),
            local_coordinates_m=Point3D(
                x_m=x_m,
                y_m=0.0,
                z_m=0.2,
            ),
            level_id=self.level.stable_id,
            level_elevation_m=0.0,
            wall_normal=UnitVector3D(
                x=1.0,
                y=0.0,
                z=0.0,
            ),
            confidence=0.95,
            evidence=SourcePointEvidence(
                kind=evidence_kind,
                method="nearest_allowed_wall_snap",
                drawing_name=self.domain.project.drawing_name,
                source_handle="WALL-101",
                observed_at=FIXED_TIME,
            ),
        )

    def equipment_source(
        self,
        *,
        source_type: CatalogSourceType = (
            CatalogSourceType.OFFICIAL_MANUFACTURER
        ),
        verification_status: CatalogSourceVerificationStatus = (
            CatalogSourceVerificationStatus.VERIFIED
        ),
        confirmed_fields: list[str] | None = None,
        manufacturer_identity: str | None | object = (
            MANUFACTURER_IDENTITY_UNSET
        ),
        publisher: str = "Example Manufacturing",
    ) -> EquipmentCatalogSource:
        verified = (
            verification_status
            == CatalogSourceVerificationStatus.VERIFIED
        )
        if manufacturer_identity is MANUFACTURER_IDENTITY_UNSET:
            normalized_identity = (
                "Example Manufacturing"
                if source_type
                == CatalogSourceType.OFFICIAL_MANUFACTURER
                else None
            )
        else:
            normalized_identity = manufacturer_identity
        return EquipmentCatalogSource(
            source_type=source_type,
            document_title="Example Product Data Sheet",
            document_version="1.0",
            document_date=FIXED_TIME.date(),
            publisher=publisher,
            manufacturer_identity=normalized_identity,
            locator="manufacturer:example/model:EX-1/revision:1.0",
            retrieved_at=FIXED_TIME,
            verification_status=verification_status,
            verification_completed_at=(
                FIXED_TIME if verified else None
            ),
            evidence_sha256=("1" * 64 if verified else None),
            confirmed_fields=(
                confirmed_fields
                if confirmed_fields is not None
                else (["model", "article"] if verified else [])
            ),
        )

    def equipment_item(
        self,
        *,
        sources: list[EquipmentCatalogSource],
        verified_fields: list[str],
        **overrides: Any,
    ) -> EquipmentCatalogItem:
        payload: dict[str, Any] = {
            "catalog_item_id": UUID(
                "9fd3cf65-7461-554a-9099-26318cf7c4b1"
            ),
            "manufacturer": "Example Manufacturing",
            "brand": "Example",
            "model": "EX-1",
            "article": "EX-1",
            "category": "test fixture",
            "verification_status": CatalogVerificationStatus.VERIFIED,
            "sources": sources,
            "verified_fields": verified_fields,
        }
        payload.update(overrides)
        return EquipmentCatalogItem(
            **payload,
        )

    def variant(
        self,
        *,
        issue_ids: list[UUID] | None = None,
    ) -> DesignVariantMetadata:
        return DesignVariantMetadata(
            variant_id=UUID(
                "03a76a58-d940-5a6f-9fa8-1f9e9ccf4878"
            ),
            kind=DesignVariantKind.BUDGET,
            revision=1,
            status=DesignVariantStatus.NOT_IMPLEMENTED,
            objective="Minimum CAPEX without reducing safety.",
            safety_baseline_sha256="0" * 64,
            issue_ids=issue_ids or [],
        )

    def issue(
        self,
        *,
        issue_id: UUID,
        severity: IssueSeverity = IssueSeverity.BLOCKING,
        status: IssueStatus = IssueStatus.OPEN,
    ) -> Issue:
        return Issue(
            issue_id=issue_id,
            code="PROJECT_FOUNDATION_TEST",
            severity=severity,
            status=status,
            message="Project foundation test issue.",
            created_at=FIXED_TIME,
            resolved_at=(
                FIXED_TIME + timedelta(minutes=1)
                if status != IssueStatus.OPEN
                else None
            ),
        )

    def canonical_project(
        self,
        *,
        domain=None,
        seed=None,
        status: ProjectLifecycleStatus = (
            ProjectLifecycleStatus.READY_FOR_DESIGN
        ),
        issues: list[Issue] | None = None,
        variants: list[DesignVariantMetadata] | None = None,
    ) -> CanonicalProjectModel:
        project_domain = domain or self.domain
        project_seed = seed or build_project_seed(
            project_domain,
            [self.boiler_point(), self.water_point()],
            created_at=FIXED_TIME,
        )
        return CanonicalProjectModel(
            project_id=project_domain.project.stable_id,
            revision=1,
            status=status,
            domain=project_domain,
            seed=project_seed,
            sheet_manifest=sheet_manifest_reference(),
            issues=issues or [],
            variants=variants or [],
        )

    def test_sheet_manifest_has_exact_130_sheet_baseline(
        self,
    ) -> None:
        manifest = load_sheet_manifest()
        self.assertEqual("1.0", manifest.schema_version)
        self.assertEqual(130, manifest.base_sheet_count)
        self.assertEqual(130, len(manifest.sheets))
        self.assertEqual(
            list(range(1, 131)),
            [sheet.number for sheet in manifest.sheets],
        )
        self.assertEqual(
            "HA-GEN-001",
            manifest.sheets[0].code,
        )
        self.assertEqual(
            "HA-SPEC-010",
            manifest.sheets[-1].code,
        )
        self.assertEqual(
            130,
            len({sheet.code for sheet in manifest.sheets}),
        )
        self.assertEqual(
            (
                "db1ab8021e4453b28e3a25771d99ea40"
                "f8d4d28eda7d6653710872cf57de1b64"
            ),
            manifest.source.sha256,
        )
        self.assertTrue(
            all(
                sheet.default_included
                for sheet in manifest.sheets
            )
        )

        groups = Counter(
            sheet.code.split("-")[1]
            for sheet in manifest.sheets
        )
        self.assertEqual(
            {
                "AUT": 4,
                "EM": 6,
                "GEN": 35,
                "OV": 25,
                "SPEC": 10,
                "TM": 21,
                "VENT": 10,
                "VK": 19,
            },
            dict(groups),
        )

    def test_canonical_preview_reuses_domain_and_is_deterministic(
        self,
    ) -> None:
        manifest = sheet_manifest_reference()
        points = [self.boiler_point(), self.water_point()]
        first = build_canonical_project_preview(
            self.domain,
            points,
            sheet_manifest=manifest,
            created_at=FIXED_TIME,
        )
        second = build_canonical_project_preview(
            self.domain,
            points,
            sheet_manifest=manifest,
            created_at=FIXED_TIME,
        )

        self.assertEqual(
            first.model_dump(mode="json"),
            second.model_dump(mode="json"),
        )
        self.assertIs(first.domain, self.domain)
        self.assertEqual(
            self.domain.diagnostics,
            first.domain.diagnostics,
        )
        self.assertEqual(
            first.seed.project_stable_id,
            self.domain.project.stable_id,
        )

    def test_sheet_manifest_reference_hashes_canonical_content(
        self,
    ) -> None:
        reference = sheet_manifest_reference()
        self.assertEqual(
            sha256_hex(
                canonical_json_bytes(load_sheet_manifest())
            ),
            reference.manifest_sha256,
        )

    def test_sheet_manifest_reference_ignores_serialization(
        self,
    ) -> None:
        payload = load_sheet_manifest().model_dump(mode="json")
        reordered = {
            key: payload[key]
            for key in reversed(payload)
        }
        reordered["sheets"] = [
            {
                key: sheet[key]
                for key in reversed(sheet)
            }
            for sheet in payload["sheets"]
        ]
        compact_lf = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        pretty_crlf = json.dumps(
            reordered,
            ensure_ascii=False,
            indent=2,
        ).replace("\n", "\r\n")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lf_path = root / "manifest-lf.json"
            crlf_path = root / "manifest-crlf.json"
            lf_path.write_bytes(compact_lf.encode("utf-8"))
            crlf_path.write_bytes(pretty_crlf.encode("utf-8"))

            lf_reference = sheet_manifest_reference(lf_path)
            crlf_reference = sheet_manifest_reference(crlf_path)

        self.assertEqual(
            lf_reference.manifest_sha256,
            crlf_reference.manifest_sha256,
        )

    def test_sheet_manifest_reference_changes_with_content(
        self,
    ) -> None:
        payload = load_sheet_manifest().model_dump(mode="json")
        changed = dict(payload)
        changed["base_building_type"] = (
            payload["base_building_type"] + " amended"
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original_path = root / "manifest-original.json"
            changed_path = root / "manifest-changed.json"
            original_path.write_bytes(canonical_json_bytes(payload))
            changed_path.write_bytes(canonical_json_bytes(changed))

            original = sheet_manifest_reference(original_path)
            amended = sheet_manifest_reference(changed_path)

        self.assertNotEqual(
            original.manifest_sha256,
            amended.manifest_sha256,
        )

    def test_sheet_manifest_reference_rejects_duplicate_key(
        self,
    ) -> None:
        text = canonical_json_bytes(
            load_sheet_manifest()
        ).decode("utf-8")
        duplicate = (
            '{"schema_version":"1.0",'
            + text[1:]
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest-duplicate.json"
            path.write_bytes(duplicate.encode("utf-8"))
            with self.assertRaises(ProjectFoundationError):
                sheet_manifest_reference(path)

    def test_sheet_manifest_rejects_duplicate_code(
        self,
    ) -> None:
        payload = load_sheet_manifest().model_dump()
        payload["sheets"][-1]["code"] = payload["sheets"][0][
            "code"
        ]
        with self.assertRaises(ValidationError):
            SheetManifest.model_validate(payload)

    def test_sheet_manifest_rejects_wrong_discipline(
        self,
    ) -> None:
        payload = load_sheet_manifest().model_dump()
        payload["sheets"][0]["discipline"] = payload["sheets"][
            -1
        ]["discipline"]
        with self.assertRaises(ValidationError):
            SheetManifest.model_validate(payload)

    def test_incomplete_seed_reports_missing_water_inlet(
        self,
    ) -> None:
        seed = build_project_seed(
            self.domain,
            [self.boiler_point()],
            created_at=FIXED_TIME,
        )
        self.assertEqual(
            ProjectSeedStatus.INCOMPLETE,
            seed.status,
        )
        self.assertEqual(
            [SourcePointKind.WATER_INLET],
            seed.missing_required_source_points,
        )

    def test_complete_seed_is_deterministic(
        self,
    ) -> None:
        points = [self.water_point(), self.boiler_point()]
        first = build_project_seed(
            self.domain,
            points,
            created_at=FIXED_TIME,
        )
        second = build_project_seed(
            self.domain,
            list(reversed(points)),
            created_at=FIXED_TIME + timedelta(hours=1),
        )
        self.assertEqual(ProjectSeedStatus.READY, first.status)
        self.assertEqual([], first.missing_required_source_points)
        self.assertEqual(first.seed_id, second.seed_id)
        self.assertEqual(first.input_sha256, second.input_sha256)
        self.assertEqual(
            [item.kind for item in first.source_points],
            [
                SourcePointKind.BOILER_ROOM,
                SourcePointKind.WATER_INLET,
            ],
        )

    def test_required_points_accept_only_human_confirmation(
        self,
    ) -> None:
        valid_combinations = (
            (
                SourcePointState.MARKED,
                SourceEvidenceKind.USER_MARKED,
            ),
            (
                SourcePointState.ACCEPTED,
                SourceEvidenceKind.USER_APPROVED,
            ),
        )
        for state, evidence_kind in valid_combinations:
            with self.subTest(
                state=state,
                evidence_kind=evidence_kind,
            ):
                seed = build_project_seed(
                    self.domain,
                    [
                        self.boiler_point(
                            state=state,
                            evidence_kind=evidence_kind,
                        ),
                        self.water_point(
                            state=state,
                            evidence_kind=evidence_kind,
                        ),
                    ],
                    created_at=FIXED_TIME,
                )
                self.assertEqual(ProjectSeedStatus.READY, seed.status)
                self.assertEqual(
                    [],
                    seed.missing_required_source_points,
                )

    def test_required_points_reject_non_human_combinations(
        self,
    ) -> None:
        invalid_combinations = (
            (
                SourcePointState.MARKED,
                SourceEvidenceKind.RULE_PROPOSED,
            ),
            (
                SourcePointState.ACCEPTED,
                SourceEvidenceKind.RULE_PROPOSED,
            ),
            (
                SourcePointState.MARKED,
                SourceEvidenceKind.USER_APPROVED,
            ),
            (
                SourcePointState.ACCEPTED,
                SourceEvidenceKind.USER_MARKED,
            ),
        )
        for state, evidence_kind in invalid_combinations:
            with self.subTest(
                state=state,
                evidence_kind=evidence_kind,
            ):
                seed = build_project_seed(
                    self.domain,
                    [
                        self.boiler_point(
                            state=state,
                            evidence_kind=evidence_kind,
                        ),
                        self.water_point(
                            state=state,
                            evidence_kind=evidence_kind,
                        ),
                    ],
                    created_at=FIXED_TIME,
                )
                self.assertEqual(
                    ProjectSeedStatus.INCOMPLETE,
                    seed.status,
                )
                self.assertEqual(
                    [
                        SourcePointKind.BOILER_ROOM,
                        SourcePointKind.WATER_INLET,
                    ],
                    seed.missing_required_source_points,
                )

    def test_seed_rejects_duplicate_source_point_id(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            build_project_seed(
                self.domain,
                [
                    self.boiler_point(),
                    self.water_point(
                        point_id=BOILER_POINT_ID,
                    ),
                ],
                created_at=FIXED_TIME,
            )

    def test_repeat_water_selection_preserves_history(
        self,
    ) -> None:
        original = build_project_seed(
            self.domain,
            [self.boiler_point(), self.water_point()],
            created_at=FIXED_TIME,
        )
        replacement = self.water_point(
            point_id=WATER_POINT_ID_V2,
            revision=2,
            x_m=4.5,
        )
        updated = replace_active_source_point(
            original,
            replacement,
            created_at=FIXED_TIME + timedelta(minutes=5),
        )

        self.assertEqual(2, updated.revision)
        water_points = [
            point
            for point in updated.source_points
            if point.kind == SourcePointKind.WATER_INLET
        ]
        self.assertEqual(2, len(water_points))
        old = next(
            point
            for point in water_points
            if point.source_point_id == WATER_POINT_ID_V1
        )
        new = next(
            point
            for point in water_points
            if point.source_point_id == WATER_POINT_ID_V2
        )
        self.assertFalse(old.active)
        self.assertEqual(SourcePointState.REPLACED, old.state)
        self.assertTrue(new.active)
        self.assertNotEqual(
            original.input_sha256,
            updated.input_sha256,
        )

    def test_water_inlet_requires_coordinate_context(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            SourcePoint(
                source_point_id=WATER_POINT_ID_V1,
                kind=SourcePointKind.WATER_INLET,
                revision=1,
                state=SourcePointState.MARKED,
                world_coordinates_m=Point3D(
                    x_m=1.0,
                    y_m=2.0,
                    z_m=0.0,
                ),
                confidence=0.8,
                evidence=SourcePointEvidence(
                    kind=SourceEvidenceKind.USER_MARKED,
                    method="manual",
                    observed_at=FIXED_TIME,
                ),
            )

    def test_boiler_room_requires_local_coordinates(self) -> None:
        payload = self.boiler_point().model_dump()
        payload["local_coordinates_m"] = None
        with self.assertRaises(ValidationError):
            SourcePoint.model_validate(payload)

    def test_boiler_room_requires_level_id(self) -> None:
        payload = self.boiler_point().model_dump()
        payload["level_id"] = None
        with self.assertRaises(ValidationError):
            SourcePoint.model_validate(payload)

    def test_active_proposed_boiler_requires_all_context(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            SourcePoint(
                source_point_id=BOILER_POINT_ID,
                kind=SourcePointKind.BOILER_ROOM,
                revision=1,
                state=SourcePointState.PROPOSED,
                active=True,
                confidence=0.1,
                evidence=SourcePointEvidence(
                    kind=SourceEvidenceKind.RULE_PROPOSED,
                    method="rule_proposal",
                    observed_at=FIXED_TIME,
                ),
            )

    def test_active_proposed_boiler_rejects_each_missing_context(
        self,
    ) -> None:
        for field_name in (
            "world_coordinates_m",
            "local_coordinates_m",
            "level_id",
            "room_id",
        ):
            with self.subTest(field_name=field_name):
                payload = self.boiler_point().model_dump()
                payload["state"] = SourcePointState.PROPOSED
                payload["evidence"] = SourcePointEvidence(
                    kind=SourceEvidenceKind.RULE_PROPOSED,
                    method="rule_proposal",
                    observed_at=FIXED_TIME,
                )
                payload[field_name] = None
                with self.assertRaises(ValidationError):
                    SourcePoint.model_validate(payload)

    def test_complete_active_proposed_boiler_is_not_ready(
        self,
    ) -> None:
        payload = self.boiler_point().model_dump()
        payload["state"] = SourcePointState.PROPOSED
        payload["evidence"] = SourcePointEvidence(
            kind=SourceEvidenceKind.RULE_PROPOSED,
            method="rule_proposal",
            observed_at=FIXED_TIME,
        )
        proposed = SourcePoint.model_validate(payload)
        self.assertTrue(proposed.active)
        self.assertFalse(proposed.is_human_confirmed())

        seed = build_project_seed(
            self.domain,
            [proposed, self.water_point()],
            created_at=FIXED_TIME,
        )
        self.assertEqual(ProjectSeedStatus.INCOMPLETE, seed.status)
        self.assertEqual(
            [SourcePointKind.BOILER_ROOM],
            seed.missing_required_source_points,
        )

    def test_incomplete_inactive_proposed_boiler_is_allowed(
        self,
    ) -> None:
        proposed = SourcePoint(
            source_point_id=BOILER_POINT_ID,
            kind=SourcePointKind.BOILER_ROOM,
            revision=1,
            state=SourcePointState.PROPOSED,
            active=False,
            confidence=0.1,
            evidence=SourcePointEvidence(
                kind=SourceEvidenceKind.RULE_PROPOSED,
                method="inactive_draft",
                observed_at=FIXED_TIME,
            ),
        )
        self.assertIsNone(proposed.world_coordinates_m)
        self.assertIsNone(proposed.local_coordinates_m)
        self.assertIsNone(proposed.level_id)
        self.assertIsNone(proposed.room_id)

    def test_active_proposed_boiler_rejects_unknown_domain_ids(
        self,
    ) -> None:
        payload = self.boiler_point().model_dump()
        payload["state"] = SourcePointState.PROPOSED
        payload["evidence"] = SourcePointEvidence(
            kind=SourceEvidenceKind.RULE_PROPOSED,
            method="rule_proposal",
            observed_at=FIXED_TIME,
        )
        payload["level_id"] = UUID(
            "c438fba1-bd03-532b-8caf-077b072ca9ce"
        )
        payload["room_id"] = UUID(
            "d37c958b-cdaf-59fa-a06f-d7414ee79a60"
        )
        proposed = SourcePoint.model_validate(payload)
        seed = build_project_seed(
            self.domain,
            [proposed, self.water_point()],
            created_at=FIXED_TIME,
        )
        with self.assertRaises(ValidationError):
            self.canonical_project(
                seed=seed,
                status=ProjectLifecycleStatus.BLOCKED,
            )

    def test_canonical_project_rejects_unknown_room_id(
        self,
    ) -> None:
        payload = self.boiler_point().model_dump()
        payload["room_id"] = UUID(
            "74014d52-c1cd-5e08-a096-dc7956d99f50"
        )
        boiler = SourcePoint.model_validate(payload)
        seed = build_project_seed(
            self.domain,
            [boiler, self.water_point()],
            created_at=FIXED_TIME,
        )
        with self.assertRaises(ValidationError):
            self.canonical_project(seed=seed)

    def test_canonical_project_rejects_unknown_level_id(
        self,
    ) -> None:
        payload = self.boiler_point().model_dump()
        payload["level_id"] = UUID(
            "20304209-c5be-54c0-995e-35ce987ab06c"
        )
        boiler = SourcePoint.model_validate(payload)
        seed = build_project_seed(
            self.domain,
            [boiler, self.water_point()],
            created_at=FIXED_TIME,
        )
        with self.assertRaises(ValidationError):
            self.canonical_project(seed=seed)

    def test_canonical_project_rejects_room_level_mismatch(
        self,
    ) -> None:
        domain = self.domain.model_copy(deep=True)
        second_level_id = UUID(
            "d2d1b051-efcf-5e28-9511-1433e5acc3a6"
        )
        second_level = self.level.model_copy(
            deep=True,
            update={
                "stable_id": second_level_id,
                "name": "Independent second level",
                "rooms": [],
            },
        )
        domain.project.buildings[0].levels.append(second_level)
        payload = self.boiler_point().model_dump()
        payload["level_id"] = second_level_id
        boiler = SourcePoint.model_validate(payload)
        seed = build_project_seed(
            domain,
            [boiler, self.water_point()],
            created_at=FIXED_TIME,
        )
        with self.assertRaises(ValidationError):
            self.canonical_project(
                domain=domain,
                seed=seed,
            )

    def test_wall_normal_must_be_unit_length(self) -> None:
        with self.assertRaises(ValidationError):
            UnitVector3D(x=1.0, y=1.0, z=0.0)

    def test_typed_numeric_fields_reject_bool(self) -> None:
        with self.assertRaises(ValidationError):
            Point3D.model_validate_json(
                '{"x_m":true,"y_m":0.0,"z_m":0.0}'
            )

    def test_source_point_json_coordinate_round_trip(
        self,
    ) -> None:
        point = self.water_point()
        restored = SourcePoint.model_validate_json(
            point.model_dump_json()
        )
        self.assertEqual(point, restored)

    def test_source_evidence_rejects_local_path(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            SourcePointEvidence(
                kind=SourceEvidenceKind.USER_MARKED,
                method="manual",
                drawing_name=(
                    "C:\\private\\project\\drawing.dwg"
                ),
                observed_at=FIXED_TIME,
            )

    def test_canonical_project_requires_shared_identity(
        self,
    ) -> None:
        seed = build_project_seed(
            self.domain,
            [self.boiler_point(), self.water_point()],
            created_at=FIXED_TIME,
        )
        project = CanonicalProjectModel(
            project_id=self.domain.project.stable_id,
            revision=1,
            status=ProjectLifecycleStatus.READY_FOR_DESIGN,
            domain=self.domain,
            seed=seed,
            sheet_manifest=sheet_manifest_reference(),
        )
        restored = CanonicalProjectModel.model_validate_json(
            project.model_dump_json()
        )
        self.assertEqual(project, restored)

        payload = project.model_dump()
        payload["project_id"] = UUID(
            "c6801e3f-833e-55e0-968a-6be838e66b7a"
        )
        with self.assertRaises(ValidationError):
            CanonicalProjectModel.model_validate(payload)

    def test_ready_project_requires_complete_seed(
        self,
    ) -> None:
        incomplete = build_project_seed(
            self.domain,
            [self.boiler_point()],
            created_at=FIXED_TIME,
        )
        with self.assertRaises(ValidationError):
            CanonicalProjectModel(
                project_id=self.domain.project.stable_id,
                revision=1,
                status=ProjectLifecycleStatus.READY_FOR_DESIGN,
                domain=self.domain,
                seed=incomplete,
                sheet_manifest=sheet_manifest_reference(),
            )

    def test_models_reject_unknown_fields(self) -> None:
        payload = self.boiler_point().model_dump()
        payload["unexpected"] = "value"
        with self.assertRaises(ValidationError):
            SourcePoint.model_validate(payload)

    def test_common_json_loader_rejects_nested_duplicate_key(
        self,
    ) -> None:
        assumption = Assumption(
            assumption_id=UUID(
                "4b118d3a-a9e4-5f0b-8522-35832ad46c81"
            ),
            description="Duplicate-key probe.",
            proposed_value={"status": "pending"},
            source_rule="STRICT_PROJECT_JSON",
            confidence=0.5,
            criticality=AssumptionCriticality.INFO,
            created_at=FIXED_TIME,
        )
        text = assumption.model_dump_json()
        duplicate = text.replace(
            '"proposed_value":{"status":"pending"}',
            (
                '"proposed_value":{'
                '"status":"first","status":"pending"}'
            ),
            1,
        )
        self.assertNotEqual(text, duplicate)
        with self.assertRaises(ProjectJsonError):
            Assumption.model_validate_json(duplicate)

    def test_common_json_loader_rejects_nonfinite_constants(
        self,
    ) -> None:
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                with self.assertRaises(ProjectJsonError):
                    Assumption.model_validate_json(
                        (
                            '{"assumption_id":'
                            '"4b118d3a-a9e4-5f0b-8522-35832ad46c81",'
                            '"description":"constant probe",'
                            f'"proposed_value":{{"value":{constant}}},'
                            '"source_rule":"STRICT_PROJECT_JSON",'
                            '"confidence":0.5,'
                            '"criticality":"info",'
                            '"status":"proposed",'
                            '"created_at":"2026-07-27T08:00:00Z"}'
                        )
                    )

    def test_assumption_json_values_require_finite_numbers(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            Assumption(
                assumption_id=UUID(
                    "e4936143-dff2-50d6-a135-a8171fffa0fc"
                ),
                description="Non-finite assumption.",
                proposed_value={
                    "deep": [{"value": math.nan}]
                },
                source_rule="FINITE_JSON",
                confidence=0.5,
                criticality=AssumptionCriticality.INFO,
                created_at=FIXED_TIME,
            )
        valid = Assumption(
            assumption_id=UUID(
                "e4936143-dff2-50d6-a135-a8171fffa0fc"
            ),
            description="Deep non-numeric assumption.",
            proposed_value={
                "deep": [{"value": "unknown", "accepted": False}]
            },
            source_rule="FINITE_JSON",
            confidence=0.5,
            criticality=AssumptionCriticality.INFO,
            created_at=FIXED_TIME,
        )
        self.assertEqual(
            "unknown",
            valid.proposed_value["deep"][0]["value"],
        )

    def test_issue_json_values_require_finite_numbers(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            Issue(
                issue_id=UUID(
                    "40b11ccf-00c1-5243-988a-e3fd832032d0"
                ),
                code="NONFINITE_ACTUAL",
                severity=IssueSeverity.WARNING,
                message="Non-finite actual value.",
                actual_value={
                    "deep": [{"value": math.inf}]
                },
                created_at=FIXED_TIME,
            )
        with self.assertRaises(ValidationError):
            Issue(
                issue_id=UUID(
                    "f4108322-e91b-580f-9b78-af6056686725"
                ),
                code="NONFINITE_ALLOWED",
                severity=IssueSeverity.WARNING,
                message="Non-finite allowed value.",
                allowed_value={
                    "deep": [{"value": -math.inf}]
                },
                created_at=FIXED_TIME,
            )
        valid = Issue(
            issue_id=UUID(
                "40b11ccf-00c1-5243-988a-e3fd832032d0"
            ),
            code="DEEP_NONNUMERIC",
            severity=IssueSeverity.INFO,
            message="Deep non-numeric values are valid.",
            actual_value={"deep": [{"value": None}]},
            allowed_value={"deep": [{"value": "pending"}]},
            created_at=FIXED_TIME,
        )
        self.assertEqual(
            "pending",
            valid.allowed_value["deep"][0]["value"],
        )

    def test_equipment_json_values_require_finite_numbers(
        self,
    ) -> None:
        base = {
            "catalog_item_id": UUID(
                "9fd3cf65-7461-554a-9099-26318cf7c4b1"
            ),
            "manufacturer": "Example Manufacturing",
            "brand": "Example",
            "model": "EX-1",
            "article": "EX-1",
            "category": "test fixture",
            "verification_status": (
                CatalogVerificationStatus.UNVERIFIED
            ),
        }
        with self.assertRaises(ValidationError):
            EquipmentCatalogItem(
                **base,
                properties={
                    "deep": [{"value": math.nan}]
                },
            )
        with self.assertRaises(ValidationError):
            EquipmentCatalogItem(
                **base,
                connection_ports=[
                    {"deep": {"value": math.inf}}
                ],
            )
        valid = EquipmentCatalogItem(
            **base,
            properties={
                "deep": [{"value": "manufacturer-data"}]
            },
            connection_ports=[
                {"deep": {"value": False}}
            ],
        )
        self.assertEqual(
            "manufacturer-data",
            valid.properties["deep"][0]["value"],
        )

    def test_audit_event_details_require_finite_numbers(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            AuditEvent(
                event_id=UUID(
                    "259b32b6-1828-5223-94d1-705e6d25d3ab"
                ),
                occurred_at=FIXED_TIME,
                actor_kind=AuditActorKind.SYSTEM,
                event_type="nonfinite_probe",
                details={
                    "deep": [{"value": math.inf}]
                },
            )
        valid = AuditEvent(
            event_id=UUID(
                "259b32b6-1828-5223-94d1-705e6d25d3ab"
            ),
            occurred_at=FIXED_TIME,
            actor_kind=AuditActorKind.SYSTEM,
            event_type="deep_nonnumeric",
            details={
                "deep": [{"value": "recorded", "flag": True}]
            },
        )
        self.assertEqual(
            "recorded",
            valid.details["deep"][0]["value"],
        )

    def test_assumption_decision_is_auditable(self) -> None:
        with self.assertRaises(ValidationError):
            Assumption(
                assumption_id=UUID(
                    "31fda160-8b72-56e1-845f-1d4a8f8c3ab3"
                ),
                description="Source point requires confirmation.",
                proposed_value={"status": "pending"},
                source_rule="PROJECT_SEED_REQUIRED_SOURCE_POINTS",
                confidence=0.0,
                criticality=AssumptionCriticality.BLOCKING,
                status=AssumptionStatus.ACCEPTED,
                created_at=FIXED_TIME,
            )

    def test_verified_catalog_item_accepts_complete_official_evidence(
        self,
    ) -> None:
        item = self.equipment_item(
            sources=[self.equipment_source()],
            verified_fields=["model", "article"],
        )
        self.assertEqual(
            CatalogVerificationStatus.VERIFIED,
            item.verification_status,
        )

    def test_verified_catalog_item_requires_verified_fields(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            self.equipment_item(
                sources=[self.equipment_source()],
                verified_fields=[],
            )

    def test_verified_catalog_item_rejects_unverified_link(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            self.equipment_item(
                sources=[
                    self.equipment_source(
                        verification_status=(
                            CatalogSourceVerificationStatus.UNVERIFIED
                        )
                    )
                ],
                verified_fields=["model"],
            )

    def test_verified_catalog_item_rejects_third_party_source(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            self.equipment_item(
                sources=[
                    self.equipment_source(
                        source_type=CatalogSourceType.THIRD_PARTY
                    )
                ],
                verified_fields=["model"],
            )

    def test_verified_source_requires_complete_metadata(self) -> None:
        with self.assertRaises(ValidationError):
            EquipmentCatalogSource(
                source_type=(
                    CatalogSourceType.OFFICIAL_MANUFACTURER
                ),
                document_title="Incomplete source",
                publisher="Example Manufacturing",
                manufacturer_identity="Example Manufacturing",
                locator="manufacturer:example/model:EX-1",
                retrieved_at=FIXED_TIME,
                verification_status=(
                    CatalogSourceVerificationStatus.VERIFIED
                ),
                verification_completed_at=FIXED_TIME,
            )

    def test_verified_field_allowlist_is_explicit(self) -> None:
        self.assertEqual(
            {
                "manufacturer",
                "brand",
                "model",
                "article",
                "category",
                "compatible_systems",
                "properties",
                "service_clearances_m",
                "connection_ports",
            },
            set(EQUIPMENT_VERIFIABLE_FIELDS),
        )

    def test_verified_field_names_are_normalized(self) -> None:
        source = self.equipment_source(
            confirmed_fields=[" Model ", "ARTICLE"],
        )
        item = self.equipment_item(
            sources=[source],
            verified_fields=[" MODEL ", "Article"],
        )
        self.assertEqual(
            ["model", "article"],
            item.verified_fields,
        )
        self.assertEqual(
            ["model", "article"],
            source.confirmed_fields,
        )

    def test_verified_field_rejects_unknown_name(self) -> None:
        with self.assertRaises(ValidationError):
            self.equipment_item(
                sources=[self.equipment_source()],
                verified_fields=["not_a_model_field"],
            )

    def test_verified_field_rejects_duplicate_name(self) -> None:
        with self.assertRaises(ValidationError):
            self.equipment_item(
                sources=[self.equipment_source()],
                verified_fields=["model", " MODEL "],
            )

    def test_verified_source_rejects_blank_publisher(self) -> None:
        payload = self.equipment_source().model_dump()
        payload["publisher"] = "   "
        with self.assertRaises(ValidationError):
            EquipmentCatalogSource.model_validate(payload)

    def test_verified_source_rejects_blank_locator(self) -> None:
        payload = self.equipment_source().model_dump()
        payload["locator"] = "\t "
        with self.assertRaises(ValidationError):
            EquipmentCatalogSource.model_validate(payload)

    def test_verified_source_identity_is_trimmed(self) -> None:
        payload = self.equipment_source().model_dump()
        payload["publisher"] = "  Example Manufacturing  "
        payload["locator"] = "  manufacturer:example/model:EX-1  "
        source = EquipmentCatalogSource.model_validate(payload)
        self.assertEqual(
            "Example Manufacturing",
            source.publisher,
        )
        self.assertEqual(
            "manufacturer:example/model:EX-1",
            source.locator,
        )

    def test_source_retrieval_time_requires_timezone(self) -> None:
        payload = self.equipment_source().model_dump()
        payload["retrieved_at"] = FIXED_TIME.replace(tzinfo=None)
        with self.assertRaises(ValidationError):
            EquipmentCatalogSource.model_validate(payload)

    def test_source_verification_time_requires_timezone(self) -> None:
        payload = self.equipment_source().model_dump()
        payload["verification_completed_at"] = (
            FIXED_TIME.replace(tzinfo=None)
        )
        with self.assertRaises(ValidationError):
            EquipmentCatalogSource.model_validate(payload)

    def test_verified_source_json_round_trip_keeps_timezone(
        self,
    ) -> None:
        source = self.equipment_source()
        restored = EquipmentCatalogSource.model_validate_json(
            source.model_dump_json()
        )
        self.assertIsNotNone(restored.retrieved_at.utcoffset())
        self.assertIsNotNone(
            restored.verification_completed_at.utcoffset()
        )

    def test_evidence_sha256_requires_exact_hex(self) -> None:
        for invalid in ("1" * 63, "1" * 65, "z" * 64):
            with self.subTest(invalid=invalid):
                payload = self.equipment_source().model_dump()
                payload["evidence_sha256"] = invalid
                with self.assertRaises(ValidationError):
                    EquipmentCatalogSource.model_validate(payload)
        payload = self.equipment_source().model_dump()
        payload["evidence_sha256"] = "ABCDEF" + "1" * 58
        source = EquipmentCatalogSource.model_validate(payload)
        self.assertEqual(
            ("abcdef" + "1" * 58),
            source.evidence_sha256,
        )

    def test_every_verified_field_requires_official_coverage(
        self,
    ) -> None:
        source = self.equipment_source(
            confirmed_fields=["model"],
        )
        with self.assertRaises(ValidationError):
            self.equipment_item(
                sources=[source],
                verified_fields=["model", "article"],
            )

    def test_verified_fields_allow_split_official_coverage(
        self,
    ) -> None:
        item = self.equipment_item(
            sources=[
                self.equipment_source(
                    confirmed_fields=["model"],
                ),
                self.equipment_source(
                    source_type=(
                        CatalogSourceType.OFFICIAL_PUBLISHER
                    ),
                    confirmed_fields=["article"],
                ),
            ],
            verified_fields=["model", "article"],
        )
        self.assertEqual(
            ["model", "article"],
            item.verified_fields,
        )

    def test_unverified_auxiliary_source_is_allowed(self) -> None:
        item = self.equipment_item(
            sources=[
                self.equipment_source(),
                self.equipment_source(
                    verification_status=(
                        CatalogSourceVerificationStatus.UNVERIFIED
                    )
                ),
            ],
            verified_fields=["model"],
        )
        self.assertEqual(
            CatalogVerificationStatus.VERIFIED,
            item.verification_status,
        )

    def test_unverified_source_cannot_claim_coverage(self) -> None:
        with self.assertRaises(ValidationError):
            self.equipment_source(
                verification_status=(
                    CatalogSourceVerificationStatus.UNVERIFIED
                ),
                confirmed_fields=["model"],
            )

    def test_catalog_strings_preserved_by_constructor(self) -> None:
        item = EquipmentCatalogItem(
            catalog_item_id=UUID(
                "c4975772-aacd-59ef-8a6a-3a7a01a1d11a"
            ),
            verification_status=CatalogVerificationStatus.UNVERIFIED,
            **PERSISTED_CATALOG_STRINGS,
        )
        for field_name, original in PERSISTED_CATALOG_STRINGS.items():
            with self.subTest(field_name=field_name):
                self.assertEqual(original, getattr(item, field_name))
        self.assertEqual(
            tuple(map(ord, PERSISTED_CATALOG_STRINGS["model"])),
            tuple(map(ord, item.model)),
        )
        self.assertEqual(
            tuple(map(ord, PERSISTED_CATALOG_STRINGS["article"])),
            tuple(map(ord, item.article)),
        )

    def test_catalog_strings_preserved_by_model_validate(
        self,
    ) -> None:
        payload = {
            "catalog_item_id": UUID(
                "c4975772-aacd-59ef-8a6a-3a7a01a1d11a"
            ),
            "verification_status":
                CatalogVerificationStatus.UNVERIFIED,
            **PERSISTED_CATALOG_STRINGS,
        }
        item = EquipmentCatalogItem.model_validate(payload)
        for field_name, original in PERSISTED_CATALOG_STRINGS.items():
            with self.subTest(field_name=field_name):
                self.assertEqual(original, getattr(item, field_name))

    def test_catalog_strings_preserved_by_model_validate_json(
        self,
    ) -> None:
        payload = {
            "catalog_item_id":
                "c4975772-aacd-59ef-8a6a-3a7a01a1d11a",
            "verification_status": "unverified",
            **PERSISTED_CATALOG_STRINGS,
        }
        item = EquipmentCatalogItem.model_validate_json(
            json.dumps(payload, ensure_ascii=False)
        )
        for field_name, original in PERSISTED_CATALOG_STRINGS.items():
            with self.subTest(field_name=field_name):
                self.assertEqual(original, getattr(item, field_name))

    def test_catalog_string_json_round_trip_preserves_code_points(
        self,
    ) -> None:
        item = EquipmentCatalogItem(
            catalog_item_id=UUID(
                "c4975772-aacd-59ef-8a6a-3a7a01a1d11a"
            ),
            verification_status=CatalogVerificationStatus.UNVERIFIED,
            **PERSISTED_CATALOG_STRINGS,
        )
        restored = EquipmentCatalogItem.model_validate_json(
            item.model_dump_json()
        )
        for field_name, original in PERSISTED_CATALOG_STRINGS.items():
            with self.subTest(field_name=field_name):
                value = getattr(restored, field_name)
                self.assertEqual(original, value)
                self.assertEqual(
                    tuple(map(ord, original)),
                    tuple(map(ord, value)),
                )

    def test_verified_string_fields_reject_whitespace_values(
        self,
    ) -> None:
        for field_name in (
            "manufacturer",
            "brand",
            "model",
            "article",
            "category",
        ):
            with self.subTest(field_name=field_name):
                source = self.equipment_source(
                    confirmed_fields=[field_name],
                )
                with self.assertRaises(ValidationError):
                    self.equipment_item(
                        sources=[source],
                        verified_fields=[field_name],
                        **{field_name: " \t "},
                    )

    def test_verified_collection_fields_reject_empty_values(
        self,
    ) -> None:
        empty_values = {
            "compatible_systems": [],
            "properties": {},
            "service_clearances_m": {},
            "connection_ports": [],
        }
        for field_name, value in empty_values.items():
            with self.subTest(field_name=field_name):
                source = self.equipment_source(
                    confirmed_fields=[field_name],
                )
                with self.assertRaises(ValidationError):
                    self.equipment_item(
                        sources=[source],
                        verified_fields=[field_name],
                        **{field_name: value},
                    )

    def test_verified_nested_values_reject_empty_content(
        self,
    ) -> None:
        empty_values = (
            None,
            " \t ",
            [],
            {},
            {"nested": []},
            [None],
        )
        for field_name in ("properties", "connection_ports"):
            for index, empty_value in enumerate(empty_values):
                with self.subTest(
                    field_name=field_name,
                    index=index,
                ):
                    source = self.equipment_source(
                        confirmed_fields=[field_name],
                    )
                    value = (
                        {"value": empty_value}
                        if field_name == "properties"
                        else [{"value": empty_value}]
                    )
                    with self.assertRaises(ValidationError):
                        self.equipment_item(
                            sources=[source],
                            verified_fields=[field_name],
                            **{field_name: value},
                        )

        source = self.equipment_source(
            confirmed_fields=["compatible_systems"],
        )
        with self.assertRaises(ValidationError):
            self.equipment_item(
                sources=[source],
                verified_fields=["compatible_systems"],
                compatible_systems=["  "],
            )

    def test_verified_values_accept_zero_and_false(
        self,
    ) -> None:
        fields = [
            "compatible_systems",
            "properties",
            "service_clearances_m",
            "connection_ports",
        ]
        source = self.equipment_source(
            confirmed_fields=fields,
        )
        item = self.equipment_item(
            sources=[source],
            verified_fields=fields,
            compatible_systems=["heating"],
            properties={
                "minimum_value": 0,
                "enabled": False,
                "nested": [{"value": 0}],
            },
            service_clearances_m={"left": 0.0},
            connection_ports=[
                {
                    "diameter": 0,
                    "enabled": False,
                }
            ],
        )
        self.assertEqual(0, item.properties["minimum_value"])
        self.assertFalse(item.properties["enabled"])
        self.assertEqual(0.0, item.service_clearances_m["left"])

    def test_official_manufacturer_identity_exact_match(
        self,
    ) -> None:
        source = self.equipment_source(
            confirmed_fields=["manufacturer"],
            manufacturer_identity="Example Manufacturing",
        )
        item = self.equipment_item(
            sources=[source],
            verified_fields=["manufacturer"],
        )
        self.assertEqual(
            "example manufacturing",
            source.manufacturer_identity,
        )
        self.assertEqual(
            "Example Manufacturing",
            item.manufacturer,
        )

    def test_official_manufacturer_identity_normalization(
        self,
    ) -> None:
        source = self.equipment_source(
            confirmed_fields=["manufacturer"],
            manufacturer_identity=(
                "  Ｅｘａｍｐｌｅ   MANUFACTURING  "
            ),
        )
        item = self.equipment_item(
            sources=[source],
            verified_fields=["manufacturer"],
            manufacturer="  Example   Manufacturing ",
        )
        self.assertEqual(
            "example manufacturing",
            source.manufacturer_identity,
        )
        self.assertEqual(
            "  Example   Manufacturing ",
            item.manufacturer,
        )

    def test_official_manufacturer_requires_identity(self) -> None:
        with self.assertRaises(ValidationError):
            self.equipment_source(
                manufacturer_identity=None,
            )

    def test_official_manufacturer_identity_must_match_item(
        self,
    ) -> None:
        source = self.equipment_source(
            confirmed_fields=["manufacturer"],
            manufacturer_identity="Different Corporation",
        )
        with self.assertRaises(ValidationError):
            self.equipment_item(
                sources=[source],
                verified_fields=["manufacturer"],
            )

    def test_publisher_may_differ_when_identity_matches(
        self,
    ) -> None:
        source = self.equipment_source(
            confirmed_fields=["manufacturer"],
            manufacturer_identity="Example Manufacturing",
            publisher="Independent Documentation Publisher",
        )
        item = self.equipment_item(
            sources=[source],
            verified_fields=["manufacturer"],
        )
        self.assertEqual(
            "Independent Documentation Publisher",
            item.sources[0].publisher,
        )

    def test_not_implemented_variant_has_no_fake_output(
        self,
    ) -> None:
        variant = DesignVariantMetadata(
            variant_id=UUID(
                "03a76a58-d940-5a6f-9fa8-1f9e9ccf4878"
            ),
            kind=DesignVariantKind.BUDGET,
            revision=1,
            status=DesignVariantStatus.NOT_IMPLEMENTED,
            objective="Minimum CAPEX without reducing safety.",
            safety_baseline_sha256="0" * 64,
        )
        self.assertIsNone(variant.generated_at)
        self.assertEqual([], variant.calculation_case_ids)

    def test_not_implemented_variant_rejects_calculation_reference(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            DesignVariantMetadata(
                variant_id=UUID(
                    "03a76a58-d940-5a6f-9fa8-1f9e9ccf4878"
                ),
                kind=DesignVariantKind.BUDGET,
                revision=1,
                status=DesignVariantStatus.NOT_IMPLEMENTED,
                objective="No fabricated calculation.",
                safety_baseline_sha256="0" * 64,
                calculation_case_ids=[
                    UUID(
                        "cae06ea2-c7aa-56b5-9331-4e5881713120"
                    )
                ],
            )

    def test_not_implemented_variant_rejects_generation_time(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            DesignVariantMetadata(
                variant_id=UUID(
                    "03a76a58-d940-5a6f-9fa8-1f9e9ccf4878"
                ),
                kind=DesignVariantKind.BUDGET,
                revision=1,
                status=DesignVariantStatus.NOT_IMPLEMENTED,
                objective="No fabricated generated result.",
                safety_baseline_sha256="0" * 64,
                generated_at=FIXED_TIME,
            )

    def test_variant_issue_ids_must_be_unique(self) -> None:
        issue_id = UUID(
            "00bbfce3-da3f-5b61-914d-2589979b419f"
        )
        with self.assertRaises(ValidationError):
            self.variant(issue_ids=[issue_id, issue_id])

    def test_variant_accepts_active_blocking_issue(self) -> None:
        issue_id = UUID(
            "00bbfce3-da3f-5b61-914d-2589979b419f"
        )
        issue = self.issue(issue_id=issue_id)
        project = self.canonical_project(
            status=ProjectLifecycleStatus.BLOCKED,
            issues=[issue],
            variants=[self.variant(issue_ids=[issue_id])],
        )
        self.assertEqual(
            issue_id,
            project.variants[0].issue_ids[0],
        )

    def test_variant_rejects_orphan_issue_in_project(self) -> None:
        issue_id = UUID(
            "00bbfce3-da3f-5b61-914d-2589979b419f"
        )
        with self.assertRaises(ValidationError):
            self.canonical_project(
                status=ProjectLifecycleStatus.BLOCKED,
                variants=[self.variant(issue_ids=[issue_id])],
            )

    def test_project_rejects_duplicate_issue_ids(self) -> None:
        issue_id = UUID(
            "00bbfce3-da3f-5b61-914d-2589979b419f"
        )
        with self.assertRaises(ValidationError):
            self.canonical_project(
                status=ProjectLifecycleStatus.BLOCKED,
                issues=[
                    self.issue(issue_id=issue_id),
                    self.issue(issue_id=issue_id),
                ],
            )

    def test_variant_rejects_nonblocking_issue(self) -> None:
        issue_id = UUID(
            "00bbfce3-da3f-5b61-914d-2589979b419f"
        )
        issue = self.issue(
            issue_id=issue_id,
            severity=IssueSeverity.WARNING,
        )
        with self.assertRaises(ValidationError):
            self.canonical_project(
                status=ProjectLifecycleStatus.BLOCKED,
                issues=[issue],
                variants=[self.variant(issue_ids=[issue_id])],
            )

    def test_variant_rejects_resolved_blocking_issue(self) -> None:
        issue_id = UUID(
            "00bbfce3-da3f-5b61-914d-2589979b419f"
        )
        issue = self.issue(
            issue_id=issue_id,
            status=IssueStatus.RESOLVED,
        )
        with self.assertRaises(ValidationError):
            self.canonical_project(
                status=ProjectLifecycleStatus.BLOCKED,
                issues=[issue],
                variants=[self.variant(issue_ids=[issue_id])],
            )

    def test_project_models_publish_json_schemas(self) -> None:
        schemas = {
            "CanonicalProjectModel":
                CanonicalProjectModel.model_json_schema(),
            "ProjectSeed": build_project_seed(
                self.domain,
                [self.boiler_point()],
                created_at=FIXED_TIME,
            ).__class__.model_json_schema(),
            "SheetManifest": SheetManifest.model_json_schema(),
            "SourcePoint": SourcePoint.model_json_schema(),
        }
        encoded = canonical_json_bytes(schemas)
        self.assertGreater(len(encoded), 1000)


if __name__ == "__main__":
    unittest.main()
