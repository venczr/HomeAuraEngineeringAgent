from __future__ import annotations

import copy
import json
import re
import unicodedata
from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid5

from pydantic import ValidationError

from agent.domain_models import (
    DomainBoundary,
    DomainBuilding,
    DomainDocument,
    DomainFileEvidence,
    DomainLevel,
    DomainProject,
    DomainRoom,
    EntityAlias,
    EntitySource,
    IfcSpaceCandidate,
    SourceKind,
    ValidationStatus,
)
from agent.ifc_space_models import IfcSpaceGeometry
from agent.rooms_api import (
    MagiCadRoom,
    RoomBoundary,
    RoomExportReport,
)


DOMAIN_NAMESPACE = UUID(
    "b62d9c24-0c2f-5e2a-8c7d-2d4bb9c98772"
)

_WINDOWS_ABSOLUTE = re.compile(
    r"(?i)(?:[a-z]:[\\/]|"
    r"\\\\[?.][\\/]|"
    r"\\\\[^\\/\s]+[\\/][^\\/\s]+)"
)
_POSIX_ABSOLUTE = re.compile(
    r"(?:^|[\s\"'=:(])/(?!/)[^/\s]+"
)
_FILE_URI = re.compile(r"(?i)file:(?://|\\\\)")

_ROOM_CORE_FIELDS = {
    "SourceHandle",
    "Code",
    "Name",
    "Position",
    "Boundary",
    "IfcSpaceGeometry",
}


class DomainAdaptationError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        diagnostics: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.diagnostics = list(diagnostics or [])


def canonical_text(value: Any) -> str:
    return unicodedata.normalize(
        "NFKC",
        str(value or ""),
    ).strip().casefold()


def canonical_handle(value: Any) -> str:
    return unicodedata.normalize(
        "NFKC",
        str(value or ""),
    ).strip().upper()


def domain_uuid_name(
    entity_type: str,
    *canonical_components: str,
) -> str:
    if not isinstance(entity_type, str):
        raise TypeError("entity_type must be a string")
    if not all(
        isinstance(component, str)
        for component in canonical_components
    ):
        raise TypeError(
            "canonical UUID components must be strings"
        )
    return json.dumps(
        [
            "homeaura-domain-id",
            1,
            entity_type,
            *canonical_components,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def domain_uuidv5(
    entity_type: str,
    *canonical_components: str,
) -> UUID:
    return uuid5(
        DOMAIN_NAMESPACE,
        domain_uuid_name(
            entity_type,
            *canonical_components,
        ),
    )


def _contains_absolute_path(value: str) -> bool:
    return bool(
        _WINDOWS_ABSOLUTE.search(value)
        or _POSIX_ABSOLUTE.search(value)
        or _FILE_URI.search(value)
    )


def _safe_file_name(value: Any) -> str | None:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return None
    return text.rstrip("/").rsplit("/", 1)[-1] or None


def _safe_identity_text(
    value: Any,
    *,
    field_name: str,
    diagnostics: list[str],
) -> str:
    text = unicodedata.normalize(
        "NFKC",
        str(value or ""),
    ).strip()
    if _contains_absolute_path(text):
        safe_name = _safe_file_name(text) or ""
        diagnostics.append(
            f"absolute path removed from {field_name}; "
            "only the final name is used"
        )
        return safe_name
    return text


def _identity_text(
    value: Any,
    *,
    field_name: str,
) -> str:
    text = unicodedata.normalize(
        "NFKC",
        str(value or ""),
    ).strip()
    if _contains_absolute_path(text):
        diagnostic = (
            f"unsafe_identity_path field={field_name}"
        )
        raise DomainAdaptationError(
            "unsafe_identity_path",
            diagnostic,
            [diagnostic],
        )
    return text


def _safe_output_text(
    value: Any,
    *,
    field_name: str,
    diagnostics: list[str],
) -> str | None:
    if value is None:
        return None
    text = str(value)
    if _contains_absolute_path(text):
        diagnostics.append(
            f"absolute path removed from {field_name}"
        )
        return "<absolute_path_redacted>"
    return text


def _portable_copy(
    value: Any,
    *,
    diagnostics: list[str],
    location: str,
) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        removed_count = 0
        for key, item in value.items():
            key_text = str(key)
            if _contains_absolute_path(key_text):
                removed_count += 1
                continue
            result[key_text] = _portable_copy(
                item,
                diagnostics=diagnostics,
                location=f"{location}.{key_text}",
            )
        if removed_count:
            diagnostics.append(
                "unsafe_mapping_key_excluded "
                f"location={location}; "
                f"removed_count={removed_count}"
            )
        return result
    if isinstance(value, list):
        return [
            _portable_copy(
                item,
                diagnostics=diagnostics,
                location=f"{location}[{index}]",
            )
            for index, item in enumerate(value)
        ]
    if isinstance(value, tuple):
        return [
            _portable_copy(
                item,
                diagnostics=diagnostics,
                location=f"{location}[{index}]",
            )
            for index, item in enumerate(value)
        ]
    if isinstance(value, str) and _contains_absolute_path(value):
        diagnostics.append(
            f"absolute path removed from {location}"
        )
        return "<absolute_path_redacted>"
    return copy.deepcopy(value)


def _unknown_fields(
    raw: Mapping[str, Any],
    known: set[str],
    location: str,
) -> list[str]:
    diagnostics: list[str] = []
    for key in raw:
        key_text = str(key)
        if key_text not in known:
            safe_key = (
                "<absolute_field_name_redacted>"
                if _contains_absolute_path(key_text)
                else key_text
            )
            diagnostics.append(
                f"unknown field retained only as diagnostic: "
                f"{location}.{safe_key}"
            )
    return diagnostics


def _validate_format_version(payload: Mapping[str, Any]) -> str:
    version = str(payload.get("FormatVersion") or "").strip()
    if version not in {"1.0", "1.1"}:
        raise DomainAdaptationError(
            "unsupported_format_version",
            f"Unsupported rooms FormatVersion: {version or '<missing>'}",
            [
                "Only explicitly supported legacy rooms versions "
                "1.0 and 1.1 are accepted."
            ],
        )
    return version


def _validation_payload(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(payload))
    rooms = copied.get("Rooms")
    if isinstance(rooms, list):
        normalized_rooms: list[Any] = []
        for room in rooms:
            if isinstance(room, Mapping):
                normalized_room = copy.deepcopy(dict(room))
                if normalized_room.get("SourceHandle") is None:
                    normalized_room["SourceHandle"] = ""
                normalized_rooms.append(normalized_room)
            else:
                normalized_rooms.append(room)
        copied["Rooms"] = normalized_rooms
    return copied


def _boundary_status(raw_room: Mapping[str, Any]) -> ValidationStatus:
    status = canonical_text(raw_room.get("geometry_status"))
    if status == "validated":
        return ValidationStatus.VALIDATED
    if status == "provisional":
        return ValidationStatus.PROVISIONAL
    if status == "missing":
        return ValidationStatus.MISSING
    if status in {"ambiguous", "invalid", "unsupported"}:
        return ValidationStatus.INVALID
    return ValidationStatus.REQUIRES_CONFIRMATION


def _make_boundary(
    raw_room: Mapping[str, Any],
    room_id: UUID,
) -> DomainBoundary | None:
    raw_boundary = raw_room.get("Boundary")
    if not isinstance(raw_boundary, Mapping):
        return None

    diagnostics = _unknown_fields(
        raw_boundary,
        set(RoomBoundary.model_fields),
        "Room.Boundary",
    )
    source_handle = canonical_handle(
        _identity_text(
            raw_boundary.get("SourceHandle"),
            field_name="Room.Boundary.SourceHandle",
        )
    )
    if not source_handle:
        raise DomainAdaptationError(
            "ambiguous_boundary_identity",
            "Boundary.SourceHandle is empty.",
            diagnostics,
        )

    stable_id = domain_uuidv5(
        "boundary",
        str(room_id),
        "handle",
        source_handle,
    )
    geometry_status = _safe_output_text(
        raw_room.get("geometry_status"),
        field_name="Room.geometry_status",
        diagnostics=diagnostics,
    ) or "requires_confirmation"
    return DomainBoundary(
        stable_id=stable_id,
        source_handle=source_handle,
        source=EntitySource(
            kind=SourceKind.LEGACY_BOUNDARY,
            system="AutoCAD",
            identifiers={
                "room_id": str(room_id),
                "handle": source_handle,
            },
        ),
        validation_status=_boundary_status(raw_room),
        geometry_status=geometry_status,
        legacy_geometry=_portable_copy(
            raw_boundary,
            diagnostics=diagnostics,
            location="Room.Boundary",
        ),
        diagnostics=diagnostics,
    )


def _candidate_status(
    geometry_status: str,
) -> ValidationStatus:
    normalized = canonical_text(geometry_status)
    if normalized in {"validated_candidate", "provisional"}:
        return ValidationStatus.PROVISIONAL
    if normalized in {"invalid", "ambiguous", "unsupported"}:
        return ValidationStatus.INVALID
    if normalized == "missing":
        return ValidationStatus.MISSING
    return ValidationStatus.REQUIRES_CONFIRMATION


def _make_ifc_candidate(
    raw_candidate: Any,
) -> IfcSpaceCandidate | None:
    if not isinstance(raw_candidate, Mapping):
        return None

    diagnostics = _unknown_fields(
        raw_candidate,
        set(IfcSpaceGeometry.model_fields),
        "Room.IfcSpaceGeometry",
    )
    ifc_file = raw_candidate.get("IfcFile")
    ifc_space = raw_candidate.get("IfcSpace")
    if not isinstance(ifc_file, Mapping):
        ifc_file = {}
    if not isinstance(ifc_space, Mapping):
        ifc_space = {}

    diagnostics.extend(
        _unknown_fields(
            ifc_file,
            {"Path", "Sha256", "Schema"},
            "Room.IfcSpaceGeometry.IfcFile",
        )
    )
    diagnostics.extend(
        _unknown_fields(
            ifc_space,
            {
                "StepId",
                "GlobalId",
                "Name",
                "LongName",
                "ObjectType",
                "PredefinedType",
                "StoreyName",
                "StoreyElevationModelUnits",
                "StoreyElevationM",
            },
            "Room.IfcSpaceGeometry.IfcSpace",
        )
    )

    raw_path = ifc_file.get("Path")
    if isinstance(raw_path, str) and _contains_absolute_path(
        raw_path
    ):
        diagnostics.append(
            "absolute path removed from "
            "Room.IfcSpaceGeometry.IfcFile.Path; safe file name, "
            "SHA-256 and IFC identifiers retained"
        )

    portable = _portable_copy(
        raw_candidate,
        diagnostics=diagnostics,
        location="Room.IfcSpaceGeometry",
    )
    portable_file = portable.get("IfcFile")
    if isinstance(portable_file, dict):
        portable_file.pop("Path", None)
        portable_file["FileName"] = _safe_file_name(raw_path)

    geometry_status = _safe_output_text(
        raw_candidate.get("geometry_status"),
        field_name="Room.IfcSpaceGeometry.geometry_status",
        diagnostics=diagnostics,
    ) or "requires_confirmation"
    global_id = _safe_output_text(
        ifc_space.get("GlobalId"),
        field_name="Room.IfcSpaceGeometry.IfcSpace.GlobalId",
        diagnostics=diagnostics,
    )
    if global_id is not None:
        global_id = global_id.strip()
    step_value = ifc_space.get("StepId")
    step_id = step_value if isinstance(step_value, int) else None

    identifiers: dict[str, str] = {}
    if global_id:
        identifiers["global_id"] = global_id
    if step_id is not None:
        identifiers["step_id"] = str(step_id)

    return IfcSpaceCandidate(
        source=EntitySource(
            kind=SourceKind.IFC_SPACE_CANDIDATE,
            system="IFC",
            identifiers=identifiers,
        ),
        validation_status=_candidate_status(geometry_status),
        geometry_status=geometry_status,
        file=DomainFileEvidence(
            file_name=_safe_file_name(raw_path),
            sha256=_safe_output_text(
                ifc_file.get("Sha256"),
                field_name=(
                    "Room.IfcSpaceGeometry.IfcFile.Sha256"
                ),
                diagnostics=diagnostics,
            ),
            ifc_schema=_safe_output_text(
                ifc_file.get("Schema"),
                field_name=(
                    "Room.IfcSpaceGeometry.IfcFile.Schema"
                ),
                diagnostics=diagnostics,
            ),
        ),
        global_id=global_id,
        step_id=step_id,
        name=_safe_output_text(
            ifc_space.get("Name"),
            field_name="Room.IfcSpaceGeometry.IfcSpace.Name",
            diagnostics=diagnostics,
        ),
        storey_name=_safe_output_text(
            ifc_space.get("StoreyName"),
            field_name=(
                "Room.IfcSpaceGeometry.IfcSpace.StoreyName"
            ),
            diagnostics=diagnostics,
        ),
        area_m2=raw_candidate.get("AreaM2"),
        perimeter_m=raw_candidate.get("PerimeterM"),
        height_m=raw_candidate.get("HeightM"),
        match_status=_safe_output_text(
            raw_candidate.get("MatchStatus"),
            field_name="Room.IfcSpaceGeometry.MatchStatus",
            diagnostics=diagnostics,
        ),
        match_method=_safe_output_text(
            raw_candidate.get("MatchMethod"),
            field_name="Room.IfcSpaceGeometry.MatchMethod",
            diagnostics=diagnostics,
        ),
        portable_payload=portable,
        diagnostics=diagnostics,
    )


def _identity_records(
    raw_rooms: list[Mapping[str, Any]],
    diagnostics: list[str],
) -> list[tuple[str, str]]:
    identities: list[tuple[str, str]] = []
    handles: dict[str, int] = {}
    codes: dict[str, tuple[int, bool]] = {}

    for index, raw_room in enumerate(raw_rooms):
        handle_was_supplied = (
            "SourceHandle" in raw_room
            and raw_room.get("SourceHandle") is not None
        )
        handle = canonical_handle(
            _identity_text(
                raw_room.get("SourceHandle"),
                field_name=f"Rooms[{index}].SourceHandle",
            )
        )
        if handle_was_supplied and not handle:
            raise DomainAdaptationError(
                "empty_source_handle",
                f"Rooms[{index}].SourceHandle normalizes to empty.",
                diagnostics,
            )

        if handle:
            raw_code = _safe_identity_text(
                raw_room.get("Code"),
                field_name=f"Rooms[{index}].Code",
                diagnostics=diagnostics,
            )
        else:
            raw_code = _identity_text(
                raw_room.get("Code"),
                field_name="Room.Code",
            )
        code = canonical_text(raw_code)
        if not code:
            raise DomainAdaptationError(
                "empty_room_code",
                f"Rooms[{index}].Code normalizes to empty.",
                diagnostics,
            )
        if code in codes:
            first, first_has_handle = codes[code]
            error_code = (
                "duplicate_room_code"
                if handle or first_has_handle
                else "duplicate_fallback_code"
            )
            raise DomainAdaptationError(
                error_code,
                f"Rooms[{first}] and Rooms[{index}] have "
                "the same normalized Code.",
                diagnostics,
            )
        codes[code] = (index, bool(handle))

        if handle:
            if handle in handles:
                first = handles[handle]
                raise DomainAdaptationError(
                    "duplicate_source_handle",
                    f"Rooms[{first}] and Rooms[{index}] have "
                    "the same SourceHandle.",
                    diagnostics,
                )
            handles[handle] = index
            identities.append(("handle", handle))
            continue

        identities.append(("code", code))

    return identities


def adapt_rooms_payload(
    payload: Mapping[str, Any],
    *,
    project_id: str,
) -> DomainDocument:
    if not isinstance(payload, Mapping):
        raise DomainAdaptationError(
            "invalid_payload",
            "rooms payload must be a Mapping.",
        )

    version = _validate_format_version(payload)
    document_diagnostics = _unknown_fields(
        payload,
        set(RoomExportReport.model_fields),
        "$",
    )

    try:
        validated = RoomExportReport.model_validate(
            _validation_payload(payload)
        )
    except ValidationError as error:
        raise DomainAdaptationError(
            "legacy_validation_failed",
            "rooms payload failed RoomExportReport validation.",
            [str(error)],
        ) from error

    raw_rooms_value = payload.get("Rooms")
    if not isinstance(raw_rooms_value, list):
        raise DomainAdaptationError(
            "legacy_validation_failed",
            "rooms payload must contain a Rooms list.",
        )
    raw_rooms: list[Mapping[str, Any]] = []
    for index, room in enumerate(raw_rooms_value):
        if not isinstance(room, Mapping):
            raise DomainAdaptationError(
                "legacy_validation_failed",
                f"Rooms[{index}] must be a Mapping.",
            )
        raw_rooms.append(room)

    project_name = _identity_text(
        project_id,
        field_name="project_id",
    )
    drawing_name = _identity_text(
        validated.DrawingName,
        field_name="DrawingName",
    )
    canonical_project = canonical_text(project_name)
    canonical_drawing = canonical_text(drawing_name)
    if not canonical_project or not canonical_drawing:
        raise DomainAdaptationError(
            "ambiguous_project_identity",
            "project_id and DrawingName must be non-empty.",
            document_diagnostics,
        )

    project_stable_id = domain_uuidv5(
        "project",
        canonical_project,
        canonical_drawing,
    )
    building_stable_id = domain_uuidv5(
        "building",
        str(project_stable_id),
        "unassigned",
    )
    level_stable_id = domain_uuidv5(
        "level",
        str(building_stable_id),
        "unassigned",
    )

    identities = _identity_records(
        raw_rooms,
        document_diagnostics,
    )
    domain_rooms: list[DomainRoom] = []

    for index, (
        raw_room,
        validated_room,
        identity,
    ) in enumerate(zip(raw_rooms, validated.Rooms, identities)):
        room_diagnostics = _unknown_fields(
            raw_room,
            set(MagiCadRoom.model_fields),
            f"$.Rooms[{index}]",
        )
        identity_kind, identity_value = identity
        if identity_kind == "handle":
            room_stable_id = domain_uuidv5(
                "room",
                str(project_stable_id),
                canonical_drawing,
                "handle",
                identity_value,
            )
            room_status = ValidationStatus.VALIDATED
            source_handle: str | None = identity_value
            source_identifiers = {
                "drawing_name": canonical_drawing,
                "handle": identity_value,
            }
        else:
            room_stable_id = domain_uuidv5(
                "room",
                str(project_stable_id),
                canonical_drawing,
                "code",
                identity_value,
            )
            room_status = ValidationStatus.REQUIRES_CONFIRMATION
            source_handle = None
            source_identifiers = {
                "drawing_name": canonical_drawing,
                "fallback_code": identity_value,
            }
            room_diagnostics.append(
                "Room identity uses Code fallback because "
                "SourceHandle is missing."
            )

        validated_dump = validated_room.model_dump(mode="json")
        legacy_attributes: dict[str, Any] = {}
        for key in raw_room:
            if (
                key in MagiCadRoom.model_fields
                and key not in _ROOM_CORE_FIELDS
            ):
                legacy_attributes[key] = _portable_copy(
                    validated_dump.get(key),
                    diagnostics=room_diagnostics,
                    location=f"$.Rooms[{index}].{key}",
                )

        position = _portable_copy(
            validated_dump.get("Position"),
            diagnostics=room_diagnostics,
            location=f"$.Rooms[{index}].Position",
        )
        boundary = _make_boundary(raw_room, room_stable_id)
        candidate = _make_ifc_candidate(
            raw_room.get("IfcSpaceGeometry")
        )

        aliases: list[EntityAlias] = []
        if candidate is not None and candidate.global_id:
            aliases.append(
                EntityAlias(
                    kind="ifc_global_id",
                    value=candidate.global_id,
                    source_kind=SourceKind.IFC_SPACE_CANDIDATE,
                )
            )

        safe_code = _safe_identity_text(
            validated_room.Code,
            field_name=f"Rooms[{index}].Code",
            diagnostics=room_diagnostics,
        )
        safe_name = _safe_identity_text(
            validated_room.Name,
            field_name=f"Rooms[{index}].Name",
            diagnostics=room_diagnostics,
        )
        domain_rooms.append(
            DomainRoom(
                stable_id=room_stable_id,
                code=safe_code,
                name=safe_name,
                source_handle=source_handle,
                source=EntitySource(
                    kind=SourceKind.LEGACY_ROOM,
                    system="MagiCAD/AutoCAD rooms export",
                    identifiers=source_identifiers,
                ),
                validation_status=room_status,
                aliases=aliases,
                position=position,
                legacy_attributes=legacy_attributes,
                boundary=boundary,
                ifc_space_candidate=candidate,
                diagnostics=room_diagnostics,
            )
        )

    level = DomainLevel(
        stable_id=level_stable_id,
        name="Unassigned Level",
        source=EntitySource(
            kind=SourceKind.LEGACY_PLACEHOLDER,
            system="DOMAIN-1 adapter",
            identifiers={"placeholder": "unassigned"},
        ),
        validation_status=(
            ValidationStatus.REQUIRES_CONFIRMATION
        ),
        rooms=domain_rooms,
        diagnostics=[
            "Legacy rooms payload has no authoritative Level."
        ],
    )
    building = DomainBuilding(
        stable_id=building_stable_id,
        name="Unassigned Building",
        source=EntitySource(
            kind=SourceKind.LEGACY_PLACEHOLDER,
            system="DOMAIN-1 adapter",
            identifiers={"placeholder": "unassigned"},
        ),
        validation_status=(
            ValidationStatus.REQUIRES_CONFIRMATION
        ),
        levels=[level],
        diagnostics=[
            "Legacy rooms payload has no authoritative Building."
        ],
    )
    project = DomainProject(
        stable_id=project_stable_id,
        name=project_name,
        drawing_name=drawing_name,
        source=EntitySource(
            kind=SourceKind.DERIVED_DETERMINISTIC,
            system="DOMAIN-1 UUIDv5 adapter",
            identifiers={
                "project_id": canonical_project,
                "drawing_name": canonical_drawing,
            },
        ),
        validation_status=(
            ValidationStatus.REQUIRES_CONFIRMATION
        ),
        buildings=[building],
        diagnostics=[
            "Project identity is deterministic but derived; "
            "renaming project_id or DrawingName changes its UUID."
        ],
    )

    if payload.get("DrawingFullPath"):
        document_diagnostics.append(
            "DrawingFullPath omitted from domain output."
        )

    return DomainDocument(
        legacy_format_version=version,
        project=project,
        diagnostics=document_diagnostics,
    )
