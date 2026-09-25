"""Shared raster occupancy state for iterative UFH route planning.

The raster is a candidate-search aid.  It deliberately does not certify pipe
geometry, bend radii, wall crossings, or hydraulics; callers must still run the
existing exact vector validators before promoting a route.

Cells are addressed as ``(row, column)`` / ``(y, x)``.  World coordinates are
millimetres.  A cell represents its complete rectangular footprint, including
the clipped final row/column when the domain size is not a multiple of the
cell size.  Clearance dilation is conservative: every cell whose rectangular
footprint can be within the requested clearance is reserved.
"""
from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from math import ceil, floor, hypot, isfinite
from types import MappingProxyType
from typing import Any, Mapping, Sequence
from uuid import uuid4

try:  # NumPy is optional in the current runtime lock; fail closed when absent.
    import numpy as np
except ImportError as exc:  # pragma: no cover - exercised through monkeypatch.
    np = None  # type: ignore[assignment]
    _NUMPY_IMPORT_ERROR: ImportError | None = exc
else:
    _NUMPY_IMPORT_ERROR = None


class RasterDependencyError(RuntimeError):
    """Raised when the accelerated raster backend is unavailable."""


class RasterDomainError(ValueError):
    """Raised for invalid dimensions, coordinates, masks, or identifiers."""


class ReservationConflictError(RuntimeError):
    """Raised when a reservation intersects blocked or occupied cells."""

    def __init__(
        self,
        message: str,
        *,
        static_cell_count: int = 0,
        occupied_cell_count: int = 0,
        boundary_overflow: bool = False,
    ) -> None:
        super().__init__(message)
        self.static_cell_count = static_cell_count
        self.occupied_cell_count = occupied_cell_count
        self.boundary_overflow = boundary_overflow


class SnapshotMismatchError(ValueError):
    """Raised when a snapshot belongs to another raster domain."""


def _require_numpy() -> Any:
    if np is None:
        raise RasterDependencyError(
            "RasterRoutingDomain requires NumPy; install and pin NumPy before "
            "using the raster routing backend"
        ) from _NUMPY_IMPORT_ERROR
    return np


def _readonly_copy(array: Any) -> Any:
    result = array.copy()
    result.flags.writeable = False
    return result


@dataclass(frozen=True)
class RasterReservation:
    """One atomic occupancy allocation.

    ``material_mask`` contains the caller-supplied footprint.  ``reserved_mask``
    also contains its clearance buffer.  Both arrays are immutable copies.
    """

    reservation_id: str
    owner: str
    role: str
    clearance_mm: float
    material_mask: Any
    reserved_mask: Any

    @property
    def material_cell_count(self) -> int:
        return int(self.material_mask.sum())

    @property
    def reserved_cell_count(self) -> int:
        return int(self.reserved_mask.sum())


@dataclass(frozen=True)
class RasterSnapshot:
    """Opaque, immutable rollback point for one domain instance."""

    domain_token: str
    static_mask: Any
    occupied_mask: Any
    owner_ids: Any
    role_ids: Any
    reservation_ids: Any
    owner_codes: Mapping[str, int]
    role_codes: Mapping[str, int]
    reservations: Mapping[str, RasterReservation]
    reservation_codes: Mapping[str, int]
    next_reservation_number: int
    revision: int


class _RasterTransaction(AbstractContextManager["_RasterTransaction"]):
    def __init__(self, domain: "RasterRoutingDomain") -> None:
        self._domain = domain
        self._snapshot = domain.snapshot()
        self._active = True

    def commit(self) -> None:
        self._active = False

    def rollback(self) -> None:
        if self._active:
            self._domain.rollback(self._snapshot)
            self._active = False

    def __enter__(self) -> "_RasterTransaction":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        return False


class RasterRoutingDomain:
    """NumPy-backed global occupancy map for one planar routing domain.

    The class keeps static obstacles separate from dynamic reservations and
    stores compact integer owner/role layers.  Public layer properties return
    copies so external code cannot bypass reservation invariants.
    """

    def __init__(
        self,
        *,
        origin_mm: tuple[float, float],
        width_mm: float,
        height_mm: float,
        cell_size_mm: float = 10.0,
        static_mask: Any | None = None,
        static_clearance_mm: float = 0.0,
    ) -> None:
        numpy = _require_numpy()
        values = (*origin_mm, width_mm, height_mm, cell_size_mm, static_clearance_mm)
        if not all(isfinite(float(value)) for value in values):
            raise RasterDomainError("Raster dimensions and origin must be finite")
        if width_mm <= 0 or height_mm <= 0 or cell_size_mm <= 0:
            raise RasterDomainError("Raster width, height, and cell size must be positive")
        if static_clearance_mm < 0:
            raise RasterDomainError("Static clearance must be non-negative")

        self.origin_mm = (float(origin_mm[0]), float(origin_mm[1]))
        self.width_mm = float(width_mm)
        self.height_mm = float(height_mm)
        self.cell_size_mm = float(cell_size_mm)
        self.shape = (
            int(ceil(self.height_mm / self.cell_size_mm)),
            int(ceil(self.width_mm / self.cell_size_mm)),
        )
        self._domain_token = uuid4().hex
        self._static_mask = numpy.zeros(self.shape, dtype=numpy.bool_)
        self._occupied_mask = numpy.zeros(self.shape, dtype=numpy.bool_)
        self._owner_ids = numpy.zeros(self.shape, dtype=numpy.int32)
        self._role_ids = numpy.zeros(self.shape, dtype=numpy.int32)
        self._reservation_ids = numpy.zeros(self.shape, dtype=numpy.int32)
        self._owner_codes: dict[str, int] = {}
        self._role_codes: dict[str, int] = {}
        self._reservations: dict[str, RasterReservation] = {}
        self._reservation_codes: dict[str, int] = {}
        self._next_reservation_number = 1
        self._revision = 0

        if static_mask is not None:
            candidate = self._coerce_mask(static_mask, name="static_mask")
            self._static_mask = self._dilate(candidate, static_clearance_mm)[0]

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def static_mask(self) -> Any:
        return self._static_mask.copy()

    @property
    def occupied_mask(self) -> Any:
        return self._occupied_mask.copy()

    @property
    def owner_id_layer(self) -> Any:
        return self._owner_ids.copy()

    @property
    def role_id_layer(self) -> Any:
        return self._role_ids.copy()

    @property
    def owner_layer(self) -> Any:
        return self._decode_layer(self._owner_ids, self._owner_codes)

    @property
    def role_layer(self) -> Any:
        return self._decode_layer(self._role_ids, self._role_codes)

    @property
    def reservations(self) -> Mapping[str, RasterReservation]:
        return MappingProxyType(dict(self._reservations))

    def material_mask_for_owner(self, owner: str) -> Any:
        """Return only the material cells reserved by ``owner``.

        The owner layer covers the complete protected reservation footprint,
        including clearance cells.  Routing code that may follow an existing
        same-owner pipe must use this query instead of treating every cell in
        ``owner_layer`` as material.
        """

        owner = self._validate_label(owner, "owner")
        material = self.empty_mask()
        for reservation in self._reservations.values():
            if reservation.owner == owner:
                material |= reservation.material_mask
        return material

    def protected_mask_for_owner(self, owner: str) -> Any:
        """Return the complete protected footprint reserved by ``owner``."""

        owner = self._validate_label(owner, "owner")
        protected = self.empty_mask()
        for reservation in self._reservations.values():
            if reservation.owner == owner:
                protected |= reservation.reserved_mask
        return protected

    def same_owner_access_mask(
        self,
        owner: str,
        *,
        join_mask: Any | None = None,
    ) -> Any:
        """Return exact same-owner cells authorized for material traversal.

        Existing material is always eligible.  A caller may additionally
        authorize an exact terminal/join mask, but every such cell must be in
        this owner's protected-only footprint.  This keeps the normal
        clearance buffer closed instead of treating it as free routing space.
        """

        owner = self._validate_label(owner, "owner")
        material = self.material_mask_for_owner(owner)
        if join_mask is None:
            return material
        join = self._coerce_mask(join_mask, name="same_owner_join_mask")
        protected_only = self.protected_mask_for_owner(owner) & ~material
        outside_protected_only = join & ~protected_only
        if outside_protected_only.any():
            raise RasterDomainError(
                "same_owner_join_mask must be a subset of the owner's "
                "protected-only footprint"
            )
        return material | join

    def dilate_mask(self, mask: Any, *, clearance_mm: float) -> Any:
        """Return the conservative in-domain clearance dilation of ``mask``."""

        candidate = self._coerce_mask(mask, name="dilation mask")
        protected, _overflow = self._dilate(candidate, clearance_mm)
        return protected

    def mm_to_cell(self, point_mm: Sequence[float]) -> tuple[int, int]:
        """Map an in-domain ``(x, y)`` point to ``(row, column)``."""
        if len(point_mm) != 2:
            raise RasterDomainError("A world point must contain exactly x and y")
        x, y = float(point_mm[0]), float(point_mm[1])
        if not isfinite(x) or not isfinite(y):
            raise RasterDomainError("World coordinates must be finite")
        local_x, local_y = x - self.origin_mm[0], y - self.origin_mm[1]
        if not (0.0 <= local_x < self.width_mm and 0.0 <= local_y < self.height_mm):
            raise RasterDomainError(f"Point {(x, y)!r} is outside the raster domain")
        return int(floor(local_y / self.cell_size_mm)), int(floor(local_x / self.cell_size_mm))

    def cell_to_mm(
        self,
        cell: Sequence[int],
        *,
        anchor: str = "center",
    ) -> tuple[float, float]:
        """Map ``(row, column)`` to its clipped lower corner or centre."""
        row, column = self._validate_cell(cell)
        x0 = self.origin_mm[0] + column * self.cell_size_mm
        y0 = self.origin_mm[1] + row * self.cell_size_mm
        x1 = min(x0 + self.cell_size_mm, self.origin_mm[0] + self.width_mm)
        y1 = min(y0 + self.cell_size_mm, self.origin_mm[1] + self.height_mm)
        if anchor == "lower":
            return x0, y0
        if anchor == "center":
            return (x0 + x1) / 2.0, (y0 + y1) / 2.0
        raise RasterDomainError("Cell anchor must be 'center' or 'lower'")

    def empty_mask(self) -> Any:
        return _require_numpy().zeros(self.shape, dtype=_require_numpy().bool_)

    def mask_from_cells(self, cells: Sequence[Sequence[int]]) -> Any:
        mask = self.empty_mask()
        for cell in cells:
            row, column = self._validate_cell(cell)
            mask[row, column] = True
        return mask

    def set_static_mask(self, mask: Any, *, clearance_mm: float = 0.0) -> None:
        """Replace static obstacles atomically, rejecting occupied overlap."""
        candidate, _ = self._dilate(self._coerce_mask(mask, name="static_mask"), clearance_mm)
        conflicts = candidate & self._occupied_mask
        if conflicts.any():
            raise ReservationConflictError(
                "Static obstacles intersect dynamic reservations",
                occupied_cell_count=int(conflicts.sum()),
            )
        self._static_mask = candidate
        self._revision += 1

    def can_reserve(
        self,
        mask: Any,
        *,
        clearance_mm: float = 0.0,
        allow_boundary_clipping: bool = False,
        owner: str | None = None,
        allow_same_owner_overlap: bool = False,
        same_owner_join_mask: Any | None = None,
    ) -> bool:
        try:
            self._prepare_reservation(
                mask,
                clearance_mm,
                allow_boundary_clipping,
                owner=owner,
                allow_same_owner_overlap=allow_same_owner_overlap,
                same_owner_join_mask=same_owner_join_mask,
            )
        except (RasterDomainError, ReservationConflictError):
            return False
        return True

    def reserve(
        self,
        mask: Any,
        *,
        owner: str,
        role: str,
        clearance_mm: float = 0.0,
        reservation_id: str | None = None,
        allow_boundary_clipping: bool = False,
        allow_same_owner_overlap: bool = False,
        same_owner_join_mask: Any | None = None,
    ) -> RasterReservation:
        """Atomically reserve a material mask and its clearance footprint.

        Same-owner overlap is explicit.  Existing material may overlap, while
        protected-only cells require an exact ``same_owner_join_mask``.  This
        supports a bounded terminal join without opening the owner's complete
        clearance buffer.  Foreign-owner overlap remains forbidden.
        """
        owner = self._validate_label(owner, "owner")
        role = self._validate_label(role, "role")
        material, protected = self._prepare_reservation(
            mask,
            clearance_mm,
            allow_boundary_clipping,
            owner=owner,
            allow_same_owner_overlap=allow_same_owner_overlap,
            same_owner_join_mask=same_owner_join_mask,
        )
        if reservation_id is None:
            reservation_id = f"reservation-{self._next_reservation_number:08d}"
        reservation_id = self._validate_label(reservation_id, "reservation_id")
        if reservation_id in self._reservations:
            raise RasterDomainError(f"Duplicate reservation id: {reservation_id}")

        owner_code = self._code_for(self._owner_codes, owner)
        role_code = self._code_for(self._role_codes, role)
        reservation_code = self._next_reservation_number
        self._next_reservation_number += 1

        record = RasterReservation(
            reservation_id=reservation_id,
            owner=owner,
            role=role,
            clearance_mm=float(clearance_mm),
            material_mask=_readonly_copy(material),
            reserved_mask=_readonly_copy(protected),
        )
        self._occupied_mask[protected] = True
        self._owner_ids[protected] = owner_code
        self._role_ids[protected] = role_code
        self._reservation_ids[protected] = reservation_code
        self._reservations[reservation_id] = record
        self._reservation_codes[reservation_id] = reservation_code
        self._revision += 1
        return record

    def release(self, reservation_id: str) -> RasterReservation:
        """Release exactly one reservation, including its clearance buffer."""
        if reservation_id not in self._reservations:
            raise RasterDomainError(f"Unknown reservation id: {reservation_id}")
        record = self._reservations[reservation_id]
        del self._reservations[reservation_id]
        del self._reservation_codes[reservation_id]
        self._rebuild_dynamic_layers()
        self._revision += 1
        return record

    def snapshot(self) -> RasterSnapshot:
        """Return an immutable full-state rollback point."""
        reservations = {
            key: RasterReservation(
                reservation_id=value.reservation_id,
                owner=value.owner,
                role=value.role,
                clearance_mm=value.clearance_mm,
                material_mask=_readonly_copy(value.material_mask),
                reserved_mask=_readonly_copy(value.reserved_mask),
            )
            for key, value in self._reservations.items()
        }
        return RasterSnapshot(
            domain_token=self._domain_token,
            static_mask=_readonly_copy(self._static_mask),
            occupied_mask=_readonly_copy(self._occupied_mask),
            owner_ids=_readonly_copy(self._owner_ids),
            role_ids=_readonly_copy(self._role_ids),
            reservation_ids=_readonly_copy(self._reservation_ids),
            owner_codes=MappingProxyType(dict(self._owner_codes)),
            role_codes=MappingProxyType(dict(self._role_codes)),
            reservations=MappingProxyType(reservations),
            reservation_codes=MappingProxyType(dict(self._reservation_codes)),
            next_reservation_number=self._next_reservation_number,
            revision=self._revision,
        )

    def rollback(self, snapshot: RasterSnapshot) -> None:
        """Restore a snapshot created by this exact domain instance."""
        if not isinstance(snapshot, RasterSnapshot) or snapshot.domain_token != self._domain_token:
            raise SnapshotMismatchError("Snapshot belongs to another raster domain")
        self._static_mask = snapshot.static_mask.copy()
        self._occupied_mask = snapshot.occupied_mask.copy()
        self._owner_ids = snapshot.owner_ids.copy()
        self._role_ids = snapshot.role_ids.copy()
        self._reservation_ids = snapshot.reservation_ids.copy()
        self._owner_codes = dict(snapshot.owner_codes)
        self._role_codes = dict(snapshot.role_codes)
        self._reservations = dict(snapshot.reservations)
        self._reservation_codes = dict(snapshot.reservation_codes)
        self._next_reservation_number = snapshot.next_reservation_number
        self._revision = snapshot.revision

    def transaction(self) -> _RasterTransaction:
        """Open a transaction that rolls back automatically on exceptions."""
        return _RasterTransaction(self)

    def _prepare_reservation(
        self,
        mask: Any,
        clearance_mm: float,
        allow_boundary_clipping: bool,
        *,
        owner: str | None = None,
        allow_same_owner_overlap: bool = False,
        same_owner_join_mask: Any | None = None,
    ) -> tuple[Any, Any]:
        material = self._coerce_mask(mask, name="reservation mask")
        if not material.any():
            raise RasterDomainError("Reservation mask must contain at least one cell")
        protected, overflow = self._dilate(material, clearance_mm)
        static_conflicts = protected & self._static_mask
        occupied_conflicts = protected & self._occupied_mask
        if allow_same_owner_overlap:
            if owner is None:
                raise RasterDomainError(
                    "owner is required when same-owner overlap is enabled"
                )
            owner = self._validate_label(owner, "owner")
            owner_protected = self.protected_mask_for_owner(owner)
            permitted_material = self.same_owner_access_mask(
                owner, join_mask=same_owner_join_mask
            )
            permitted_overlap = permitted_material
            foreign_conflicts = protected & self._occupied_mask & ~owner_protected
            same_owner_conflicts = protected & owner_protected & ~permitted_overlap
            occupied_conflicts = foreign_conflicts | same_owner_conflicts
        elif same_owner_join_mask is not None:
            raise RasterDomainError(
                "same_owner_join_mask requires allow_same_owner_overlap=True"
            )
        boundary_conflict = overflow and not allow_boundary_clipping
        if static_conflicts.any() or occupied_conflicts.any() or boundary_conflict:
            raise ReservationConflictError(
                "Reservation intersects blocked, occupied, or out-of-domain cells",
                static_cell_count=int(static_conflicts.sum()),
                occupied_cell_count=int(occupied_conflicts.sum()),
                boundary_overflow=boundary_conflict,
            )
        return material, protected

    def _rebuild_dynamic_layers(self) -> None:
        """Rebuild compact display/query layers from reservation records.

        Rebuilding makes release correct when several reservations of the same
        owner overlap at an explicitly authorized joint.  Later reservations win
        only in the single-value role/reservation display layers; every exact
        material and protected mask remains available in ``reservations``.
        """

        self._occupied_mask.fill(False)
        self._owner_ids.fill(0)
        self._role_ids.fill(0)
        self._reservation_ids.fill(0)
        for reservation_id, record in self._reservations.items():
            protected = record.reserved_mask
            owner_code = self._owner_codes[record.owner]
            role_code = self._role_codes[record.role]
            reservation_code = self._reservation_codes[reservation_id]
            self._occupied_mask[protected] = True
            self._owner_ids[protected] = owner_code
            self._role_ids[protected] = role_code
            self._reservation_ids[protected] = reservation_code

    def _dilate(self, mask: Any, clearance_mm: float) -> tuple[Any, bool]:
        if not isfinite(float(clearance_mm)) or clearance_mm < 0:
            raise RasterDomainError("Clearance must be finite and non-negative")
        result = mask.copy()
        if clearance_mm == 0:
            return result, False
        radius = int(ceil(clearance_mm / self.cell_size_mm)) + 1
        offsets: list[tuple[int, int]] = []
        for delta_row in range(-radius, radius + 1):
            for delta_column in range(-radius, radius + 1):
                gap_x = max(abs(delta_column) - 1, 0) * self.cell_size_mm
                gap_y = max(abs(delta_row) - 1, 0) * self.cell_size_mm
                if hypot(gap_x, gap_y) <= clearance_mm + 1e-12:
                    offsets.append((delta_row, delta_column))

        result.fill(False)
        overflow = False
        rows, columns = self.shape
        for delta_row, delta_column in offsets:
            source_row_start = max(0, -delta_row)
            source_row_end = min(rows, rows - delta_row)
            source_column_start = max(0, -delta_column)
            source_column_end = min(columns, columns - delta_column)
            if source_row_start >= source_row_end or source_column_start >= source_column_end:
                if mask.any():
                    overflow = True
                continue
            target_rows = slice(source_row_start + delta_row, source_row_end + delta_row)
            target_columns = slice(source_column_start + delta_column, source_column_end + delta_column)
            source_rows = slice(source_row_start, source_row_end)
            source_columns = slice(source_column_start, source_column_end)
            result[target_rows, target_columns] |= mask[source_rows, source_columns]

            if delta_row < 0 and mask[: -delta_row, :].any():
                overflow = True
            elif delta_row > 0 and mask[rows - delta_row :, :].any():
                overflow = True
            if delta_column < 0 and mask[:, : -delta_column].any():
                overflow = True
            elif delta_column > 0 and mask[:, columns - delta_column :].any():
                overflow = True
        return result, overflow

    def _coerce_mask(self, mask: Any, *, name: str) -> Any:
        numpy = _require_numpy()
        candidate = numpy.asarray(mask)
        if candidate.shape != self.shape:
            raise RasterDomainError(
                f"{name} shape {candidate.shape!r} does not match domain shape {self.shape!r}"
            )
        if candidate.dtype.kind != "b":
            raise RasterDomainError(f"{name} must have Boolean dtype")
        return candidate.astype(numpy.bool_, copy=True)

    def _validate_cell(self, cell: Sequence[int]) -> tuple[int, int]:
        if len(cell) != 2 or any(isinstance(value, bool) for value in cell):
            raise RasterDomainError("A cell must contain exactly integer row and column")
        if any(int(value) != value for value in cell):
            raise RasterDomainError("Cell row and column must be integers")
        row, column = int(cell[0]), int(cell[1])
        if not (0 <= row < self.shape[0] and 0 <= column < self.shape[1]):
            raise RasterDomainError(f"Cell {(row, column)!r} is outside the raster domain")
        return row, column

    @staticmethod
    def _validate_label(value: str, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise RasterDomainError(f"{name} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _code_for(registry: dict[str, int], label: str) -> int:
        if label not in registry:
            registry[label] = len(registry) + 1
        return registry[label]

    @staticmethod
    def _decode_layer(layer: Any, registry: Mapping[str, int]) -> Any:
        numpy = _require_numpy()
        decoded = numpy.empty(layer.shape, dtype=object)
        decoded.fill(None)
        for label, code in registry.items():
            decoded[layer == code] = label
        return decoded


# ``WorldState`` is the building-planner-facing name.  The alias keeps the
# minimal core single-sourced until vector and multi-floor layers are added.
WorldState = RasterRoutingDomain


__all__ = [
    "RasterDependencyError",
    "RasterDomainError",
    "RasterReservation",
    "RasterRoutingDomain",
    "RasterSnapshot",
    "ReservationConflictError",
    "SnapshotMismatchError",
    "WorldState",
]
