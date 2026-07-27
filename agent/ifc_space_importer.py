from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import math
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent.ifc_space_models import (
    IfcBoundaryLoop,
    IfcFileInfo,
    IfcPoint3D,
    IfcRepresentationInfo,
    IfcSpaceGeometry,
    IfcSpaceImportResult,
    IfcSpaceImportSummary,
    IfcSpaceInfo,
    IfcUnitInfo,
)


SOURCE_NAME = "MagiCADRoomIfcSpace"
POINT_TOLERANCE_M = 1.0e-8
PLANARITY_TOLERANCE_M = 1.0e-6
TRIANGULATION_AREA_ABSOLUTE_TOLERANCE_M2 = 1.0e-7
TRIANGULATION_AREA_RELATIVE_TOLERANCE = 1.0e-7


class IfcSpaceImportError(RuntimeError):
    pass


class IfcOpenShellUnavailable(IfcSpaceImportError):
    pass


class IfcGeometryUnsupported(IfcSpaceImportError):
    pass


class IfcGeometryInvalid(IfcSpaceImportError):
    pass


@dataclass(frozen=True)
class IfcModules:
    root: Any
    geom: Any
    element: Any
    placement: Any
    unit: Any


@dataclass
class ParsedSpace:
    entity: Any
    info: IfcSpaceInfo
    geometry: IfcSpaceGeometry | None
    geometry_status: str
    diagnostics: list[str]


@dataclass
class MatchProposal:
    parsed: ParsedSpace
    room_index: int
    method: str


@dataclass
class IfcImportOutcome:
    rooms_document: dict[str, Any]
    summary: IfcSpaceImportSummary
    matched_geometries: list[IfcSpaceGeometry]

    def analysis_payload(self) -> dict[str, Any]:
        return {
            "IfcSpaceImport": self.summary.model_dump(mode="json"),
            "MatchedIfcSpaceGeometry": [
                geometry.model_dump(mode="json")
                for geometry in self.matched_geometries
            ],
        }


def _load_ifcopenshell() -> IfcModules:
    try:
        root = importlib.import_module("ifcopenshell")
        geom = importlib.import_module("ifcopenshell.geom")
        element = importlib.import_module(
            "ifcopenshell.util.element"
        )
        placement = importlib.import_module(
            "ifcopenshell.util.placement"
        )
        unit = importlib.import_module("ifcopenshell.util.unit")
    except (ImportError, ModuleNotFoundError) as error:
        raise IfcOpenShellUnavailable(
            "IfcOpenShell не установлен. Основной API продолжает "
            "работать без него; для IFC-импорта установите "
            "`python -m pip install -r requirements-ifc.txt`."
        ) from error

    return IfcModules(
        root=root,
        geom=geom,
        element=element,
        placement=placement,
        unit=unit,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _normalize_identifier(value: Any) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKC", str(value))
    return " ".join(normalized.split()).casefold()


def _point_distance(left: list[float], right: list[float]) -> float:
    return math.sqrt(
        sum(
            (left[index] - right[index]) ** 2
            for index in range(3)
        )
    )


def _matrix_to_lists(matrix: Any) -> list[list[float]]:
    if hasattr(matrix, "tolist"):
        values = matrix.tolist()
        return [
            [float(coordinate) for coordinate in row]
            for row in values
        ]

    values = [float(value) for value in matrix]
    if len(values) != 16:
        raise IfcGeometryInvalid(
            "Матрица размещения должна содержать 16 значений."
        )
    return [
        values[index : index + 4]
        for index in range(0, 16, 4)
    ]


def _matrix_multiply(
    left: list[list[float]],
    right: list[list[float]],
) -> list[list[float]]:
    return [
        [
            sum(left[row][inner] * right[inner][column]
                for inner in range(4))
            for column in range(4)
        ]
        for row in range(4)
    ]


def _matrix_translation_to_meters(
    matrix: list[list[float]],
    scale: float,
) -> list[list[float]]:
    result = [list(row) for row in matrix]
    for axis in range(3):
        result[axis][3] *= scale
    return result


def _transform_point(
    matrix: list[list[float]],
    point: list[float],
) -> list[float]:
    x, y, z = point
    return [
        matrix[0][0] * x
        + matrix[0][1] * y
        + matrix[0][2] * z
        + matrix[0][3],
        matrix[1][0] * x
        + matrix[1][1] * y
        + matrix[1][2] * z
        + matrix[1][3],
        matrix[2][0] * x
        + matrix[2][1] * y
        + matrix[2][2] * z
        + matrix[2][3],
    ]


def _transform_vector(
    matrix: list[list[float]],
    vector: list[float],
) -> list[float]:
    x, y, z = vector
    return [
        matrix[0][0] * x
        + matrix[0][1] * y
        + matrix[0][2] * z,
        matrix[1][0] * x
        + matrix[1][1] * y
        + matrix[1][2] * z,
        matrix[2][0] * x
        + matrix[2][1] * y
        + matrix[2][2] * z,
    ]


def _scale_point(point: list[float], scale: float) -> list[float]:
    return [coordinate * scale for coordinate in point]


def _point_model(point: list[float]) -> IfcPoint3D:
    return IfcPoint3D(X=point[0], Y=point[1], Z=point[2])


def _vector_subtract(
    left: list[float],
    right: list[float],
) -> list[float]:
    return [
        left[index] - right[index]
        for index in range(3)
    ]


def _dot(left: list[float], right: list[float]) -> float:
    return sum(
        left[index] * right[index]
        for index in range(3)
    )


def _cross(left: list[float], right: list[float]) -> list[float]:
    return [
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    ]


def _norm(vector: list[float]) -> float:
    return math.sqrt(_dot(vector, vector))


def _normalize_vector(vector: list[float]) -> list[float]:
    length = _norm(vector)
    if not math.isfinite(length) or length <= 0:
        raise IfcGeometryInvalid(
            "Направление экструзии имеет нулевую длину."
        )
    return [component / length for component in vector]


def _signed_area_xy(points: list[list[float]]) -> float:
    return 0.5 * sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0]
        * points[index][1]
        for index in range(len(points))
    )


def _perimeter(points: list[list[float]]) -> float:
    return sum(
        _point_distance(
            points[index],
            points[(index + 1) % len(points)],
        )
        for index in range(len(points))
    )


def _orientation(
    first: list[float],
    second: list[float],
    third: list[float],
    tolerance: float,
) -> int:
    value = (
        (second[1] - first[1]) * (third[0] - second[0])
        - (second[0] - first[0]) * (third[1] - second[1])
    )
    if abs(value) <= tolerance:
        return 0
    return 1 if value > 0 else 2


def _on_segment(
    first: list[float],
    point: list[float],
    second: list[float],
    tolerance: float,
) -> bool:
    return (
        min(first[0], second[0]) - tolerance
        <= point[0]
        <= max(first[0], second[0]) + tolerance
        and min(first[1], second[1]) - tolerance
        <= point[1]
        <= max(first[1], second[1]) + tolerance
    )


def _segments_intersect(
    first_start: list[float],
    first_end: list[float],
    second_start: list[float],
    second_end: list[float],
    tolerance: float,
) -> bool:
    orientation_1 = _orientation(
        first_start,
        first_end,
        second_start,
        tolerance,
    )
    orientation_2 = _orientation(
        first_start,
        first_end,
        second_end,
        tolerance,
    )
    orientation_3 = _orientation(
        second_start,
        second_end,
        first_start,
        tolerance,
    )
    orientation_4 = _orientation(
        second_start,
        second_end,
        first_end,
        tolerance,
    )

    if (
        orientation_1 != orientation_2
        and orientation_3 != orientation_4
    ):
        return True

    checks = (
        (
            orientation_1 == 0,
            first_start,
            second_start,
            first_end,
        ),
        (
            orientation_2 == 0,
            first_start,
            second_end,
            first_end,
        ),
        (
            orientation_3 == 0,
            second_start,
            first_start,
            second_end,
        ),
        (
            orientation_4 == 0,
            second_start,
            first_end,
            second_end,
        ),
    )
    return any(
        is_collinear
        and _on_segment(start, point, end, tolerance)
        for is_collinear, start, point, end in checks
    )


def _is_self_intersecting(
    points: list[list[float]],
    tolerance: float,
) -> bool:
    count = len(points)
    for first_index in range(count):
        first_next = (first_index + 1) % count
        for second_index in range(first_index + 1, count):
            second_next = (second_index + 1) % count
            if (
                first_index == second_index
                or first_next == second_index
                or second_next == first_index
            ):
                continue
            if (
                first_index == 0
                and second_next == 0
            ):
                continue
            if _segments_intersect(
                points[first_index],
                points[first_next],
                points[second_index],
                points[second_next],
                tolerance,
            ):
                return True
    return False


def _distinct_vertex_count(
    points: list[list[float]],
    tolerance: float,
) -> int:
    distinct: list[list[float]] = []
    for point in points:
        if not any(
            _point_distance(point, existing) <= tolerance
            for existing in distinct
        ):
            distinct.append(point)
    return len(distinct)


def _remove_consecutive_duplicates(
    points: list[list[float]],
    tolerance: float,
) -> tuple[list[list[float]], int]:
    result: list[list[float]] = []
    removed = 0
    for point in points:
        if (
            result
            and _point_distance(point, result[-1]) <= tolerance
        ):
            removed += 1
            continue
        result.append(point)
    return result, removed


def _planarity(
    points: list[list[float]],
) -> tuple[bool, float]:
    if len(points) < 3:
        return False, math.inf

    origin = points[0]
    normal: list[float] | None = None
    for first_index in range(1, len(points) - 1):
        for second_index in range(first_index + 1, len(points)):
            candidate = _cross(
                _vector_subtract(points[first_index], origin),
                _vector_subtract(points[second_index], origin),
            )
            if _norm(candidate) > POINT_TOLERANCE_M:
                normal = _normalize_vector(candidate)
                break
        if normal is not None:
            break

    if normal is None:
        return False, math.inf

    deviation = max(
        abs(_dot(_vector_subtract(point, origin), normal))
        for point in points
    )
    return deviation <= PLANARITY_TOLERANCE_M, deviation


def _point_in_polygon(
    point: list[float],
    polygon: list[list[float]],
) -> bool:
    inside = False
    x, y = point[0], point[1]
    previous = len(polygon) - 1
    for current in range(len(polygon)):
        current_x, current_y = polygon[current][0], polygon[current][1]
        previous_x, previous_y = (
            polygon[previous][0],
            polygon[previous][1],
        )
        if (
            (current_y > y) != (previous_y > y)
            and x
            < (previous_x - current_x)
            * (y - current_y)
            / (previous_y - current_y)
            + current_x
        ):
            inside = not inside
        previous = current
    return inside


def _unit_name(unit_entity: Any) -> str:
    if unit_entity is None:
        return "unknown"
    if unit_entity.is_a("IfcSIUnit"):
        prefix = str(unit_entity.Prefix or "").lower()
        name = str(unit_entity.Name or "").lower()
        if prefix == "milli" and name == "metre":
            return "millimetre"
        return f"{prefix}{name}" if prefix else name
    return unit_entity.is_a()


def _read_units(
    model: Any,
    modules: IfcModules,
) -> IfcUnitInfo:
    length_entity = modules.unit.get_project_unit(
        model,
        "LENGTHUNIT",
    )
    area_entity = modules.unit.get_project_unit(
        model,
        "AREAUNIT",
    )
    scale = float(modules.unit.calculate_unit_scale(model))
    if not math.isfinite(scale) or scale <= 0:
        raise IfcGeometryInvalid(
            "IfcUnitAssignment задаёт некорректную единицу длины."
        )
    return IfcUnitInfo(
        LengthUnit=_unit_name(length_entity),
        MetersPerLengthUnit=scale,
        AreaUnit=_unit_name(area_entity),
    )


def _storey_info(
    space: Any,
    modules: IfcModules,
    scale: float,
) -> tuple[str | None, float | None, float | None]:
    storey = None
    for relation in getattr(space, "Decomposes", None) or []:
        candidate = getattr(relation, "RelatingObject", None)
        if candidate is not None and candidate.is_a(
            "IfcBuildingStorey"
        ):
            storey = candidate
            break
    if storey is None:
        storey = modules.element.get_container(
            space,
            ifc_class="IfcBuildingStorey",
        )
    if storey is None:
        return None, None, None
    elevation = getattr(storey, "Elevation", None)
    return (
        getattr(storey, "Name", None),
        float(elevation) if elevation is not None else None,
        float(elevation) * scale
        if elevation is not None
        else None,
    )


def _space_info(
    space: Any,
    modules: IfcModules,
    scale: float,
) -> IfcSpaceInfo:
    storey_name, storey_elevation, storey_elevation_m = (
        _storey_info(space, modules, scale)
    )
    return IfcSpaceInfo(
        StepId=space.id(),
        GlobalId=str(space.GlobalId),
        Name=getattr(space, "Name", None),
        LongName=getattr(space, "LongName", None),
        ObjectType=getattr(space, "ObjectType", None),
        PredefinedType=str(
            getattr(space, "PredefinedType", None)
        )
        if getattr(space, "PredefinedType", None) is not None
        else None,
        StoreyName=storey_name,
        StoreyElevationModelUnits=storey_elevation,
        StoreyElevationM=storey_elevation_m,
    )


def _line_index_values(segment: Any) -> list[int]:
    try:
        values = list(segment)
    except TypeError as error:
        raise IfcGeometryUnsupported(
            "IfcIndexedPolyCurve содержит сегмент, который нельзя "
            "прочитать как IfcLineIndex."
        ) from error
    if len(values) == 1 and isinstance(values[0], (tuple, list)):
        values = list(values[0])
    return [int(value) for value in values]


def _indexed_curve_points(curve: Any) -> list[list[float]]:
    if not curve.is_a("IfcIndexedPolyCurve"):
        raise IfcGeometryUnsupported(
            "Поддерживается только IfcIndexedPolyCurve; найден "
            f"{curve.is_a()}."
        )

    point_list = getattr(curve, "Points", None)
    if point_list is None:
        raise IfcGeometryInvalid(
            "IfcIndexedPolyCurve не содержит списка точек."
        )
    if not point_list.is_a("IfcCartesianPointList2D"):
        raise IfcGeometryUnsupported(
            "Поддерживается только IfcCartesianPointList2D; найден "
            f"{point_list.is_a()}."
        )

    coordinates = [
        [float(value) for value in point]
        for point in point_list.CoordList
    ]
    if not coordinates:
        raise IfcGeometryInvalid(
            "IfcIndexedPolyCurve не содержит координат."
        )

    segments = getattr(curve, "Segments", None)
    if not segments:
        selected = coordinates
    else:
        indices: list[int] = []
        for segment in segments:
            if not segment.is_a("IfcLineIndex"):
                raise IfcGeometryUnsupported(
                    "Дуговой или иной нелинейный сегмент "
                    f"{segment.is_a()} в IfcIndexedPolyCurve пока "
                    "не поддерживается и не аппроксимируется."
                )
            segment_indices = _line_index_values(segment)
            if indices and segment_indices:
                if indices[-1] == segment_indices[0]:
                    segment_indices = segment_indices[1:]
            indices.extend(segment_indices)
        try:
            selected = [
                coordinates[index - 1]
                for index in indices
            ]
        except IndexError as error:
            raise IfcGeometryInvalid(
                "IfcLineIndex ссылается на отсутствующую точку."
            ) from error

    result: list[list[float]] = []
    for point in selected:
        if len(point) == 2:
            result.append([point[0], point[1], 0.0])
        elif len(point) == 3:
            result.append(point)
        else:
            raise IfcGeometryInvalid(
                "Точка профиля должна иметь 2 или 3 координаты."
            )
    return result


def _parse_loop(
    curve: Any,
    solid_matrix: list[list[float]],
    object_matrix: list[list[float]],
    scale: float,
    *,
    is_outer: bool,
) -> IfcBoundaryLoop:
    raw_source = _indexed_curve_points(curve)
    tolerance_model = POINT_TOLERANCE_M / scale
    source, duplicates_removed = _remove_consecutive_duplicates(
        raw_source,
        tolerance_model,
    )

    source_had_repeated_endpoint = (
        len(source) >= 2
        and _point_distance(source[0], source[-1])
        <= tolerance_model
    )
    if source_had_repeated_endpoint:
        source = source[:-1]
        closure_method = "explicit_repeated_endpoint"
    else:
        closure_method = "ifc_closed_profile_semantics"

    distinct_count = _distinct_vertex_count(
        source,
        tolerance_model,
    )
    if distinct_count < 3:
        raise IfcGeometryInvalid(
            "Замкнутый профиль должен содержать не менее трёх "
            f"различных вершин; найдено {distinct_count}."
        )

    self_intersecting = _is_self_intersecting(
        source,
        tolerance_model,
    )
    if self_intersecting:
        raise IfcGeometryInvalid(
            "Профиль содержит самопересечение."
        )

    source_m = [_scale_point(point, scale) for point in source]
    signed_area_m2 = _signed_area_xy(source_m)
    if (
        not math.isfinite(signed_area_m2)
        or abs(signed_area_m2)
        <= POINT_TOLERANCE_M * POINT_TOLERANCE_M
    ):
        raise IfcGeometryInvalid(
            "Площадь аналитического профиля равна нулю."
        )
    original_direction = (
        "CCW" if signed_area_m2 > 0 else "CW"
    )

    desired_direction = "CCW" if is_outer else "CW"
    normalized_source = list(source)
    if original_direction != desired_direction:
        normalized_source.reverse()

    local_model = [
        _transform_point(solid_matrix, point)
        for point in normalized_source
    ]
    world_model = [
        _transform_point(object_matrix, point)
        for point in local_model
    ]
    local_m = [_scale_point(point, scale) for point in local_model]
    world_m = [_scale_point(point, scale) for point in world_model]

    is_planar, z_deviation_m = _planarity(world_m)
    if not is_planar:
        raise IfcGeometryInvalid(
            "Профиль после применения IfcLocalPlacement непланарен: "
            f"отклонение {z_deviation_m} м."
        )

    return IfcBoundaryLoop(
        SourceVertices=[_point_model(point) for point in raw_source],
        LocalVertices=[_point_model(point) for point in local_m],
        WorldVertices=[_point_model(point) for point in world_m],
        IsClosed=True,
        ClosureMethod=closure_method,
        SourceHadRepeatedEndpoint=source_had_repeated_endpoint,
        DuplicateVerticesRemoved=duplicates_removed,
        DistinctVertexCount=distinct_count,
        OriginalDirection=original_direction,
        Direction=desired_direction,
        IsSelfIntersecting=False,
        IsPlanar=True,
        ZDeviationM=z_deviation_m,
        AreaM2=abs(signed_area_m2),
        PerimeterM=_perimeter(
            [_scale_point(point, scale) for point in normalized_source]
        ),
    )


def _loop_xyz(loop: IfcBoundaryLoop) -> list[list[float]]:
    return [
        [point.X, point.Y, point.Z]
        for point in loop.WorldVertices
    ]


def _loops_intersect(
    left: list[list[float]],
    right: list[list[float]],
) -> bool:
    for left_index in range(len(left)):
        left_next = (left_index + 1) % len(left)
        for right_index in range(len(right)):
            right_next = (right_index + 1) % len(right)
            if _segments_intersect(
                left[left_index],
                left[left_next],
                right[right_index],
                right[right_next],
                POINT_TOLERANCE_M,
            ):
                return True
    return False


def _validate_holes(
    outer: IfcBoundaryLoop,
    holes: list[IfcBoundaryLoop],
) -> None:
    outer_points = _loop_xyz(outer)
    checked_holes: list[list[list[float]]] = []
    for hole_index, hole in enumerate(holes, start=1):
        hole_points = _loop_xyz(hole)
        if (
            not hole_points
            or not all(
                _point_in_polygon(point, outer_points)
                for point in hole_points
            )
            or _loops_intersect(hole_points, outer_points)
        ):
            raise IfcGeometryInvalid(
                "Внутренний boundary loop "
                f"{hole_index} расположен вне наружного или пересекает его."
            )
        for previous_index, previous_points in enumerate(
            checked_holes,
            start=1,
        ):
            if (
                _loops_intersect(hole_points, previous_points)
                or _point_in_polygon(hole_points[0], previous_points)
                or _point_in_polygon(previous_points[0], hole_points)
            ):
                raise IfcGeometryInvalid(
                    "Внутренние boundary loops "
                    f"{previous_index} и {hole_index} пересекаются "
                    "или вложены друг в друга."
                )
        checked_holes.append(hole_points)


def _triangle_area(
    first: list[float],
    second: list[float],
    third: list[float],
) -> float:
    return 0.5 * _norm(
        _cross(
            _vector_subtract(second, first),
            _vector_subtract(third, first),
        )
    )


def _triangulation_check(
    model: Any,
    space: Any,
    modules: IfcModules,
    world_extrusion_axis: list[float],
) -> tuple[int, int, float]:
    settings = modules.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    shape = modules.geom.create_shape(settings, space)

    values = [float(value) for value in shape.geometry.verts]
    vertices = [
        values[index : index + 3]
        for index in range(0, len(values), 3)
    ]
    indices = [int(value) for value in shape.geometry.faces]
    triangles = [
        indices[index : index + 3]
        for index in range(0, len(indices), 3)
    ]
    if not vertices or not triangles:
        raise IfcGeometryInvalid(
            "IfcOpenShell не создал проверочную триангуляцию."
        )

    projections = [
        _dot(vertex, world_extrusion_axis)
        for vertex in vertices
    ]
    minimum_projection = min(projections)
    projection_tolerance = 1.0e-7
    bottom_area = 0.0
    bottom_triangle_count = 0
    for triangle in triangles:
        triangle_projections = [
            projections[index]
            for index in triangle
        ]
        if all(
            abs(value - minimum_projection)
            <= projection_tolerance
            for value in triangle_projections
        ):
            bottom_triangle_count += 1
            bottom_area += _triangle_area(
                vertices[triangle[0]],
                vertices[triangle[1]],
                vertices[triangle[2]],
            )

    if bottom_triangle_count == 0:
        raise IfcGeometryInvalid(
            "В триангуляции не найдена нижняя грань IfcSpace."
        )
    return len(vertices), len(triangles), bottom_area


def _find_supported_solid(
    space: Any,
) -> tuple[Any, Any]:
    product_shape = getattr(space, "Representation", None)
    if product_shape is None:
        raise IfcGeometryUnsupported(
            "IfcSpace не содержит Representation."
        )

    representations = list(product_shape.Representations)
    solid_items: list[tuple[Any, Any]] = []
    described: list[str] = []
    for representation in representations:
        item_types = [
            item.is_a()
            for item in representation.Items
        ]
        described.append(
            f"{representation.RepresentationIdentifier}/"
            f"{representation.RepresentationType}:"
            f"{','.join(item_types) or '<empty>'}"
        )
        for item in representation.Items:
            if item.is_a("IfcExtrudedAreaSolid"):
                solid_items.append((representation, item))

    if len(solid_items) != 1:
        description = "; ".join(described) or "<none>"
        raise IfcGeometryUnsupported(
            "Поддерживается ровно один IfcExtrudedAreaSolid; "
            f"найдено {len(solid_items)}. Представления: "
            f"{description}."
        )
    return solid_items[0]


def _parse_space_geometry(
    model: Any,
    space: Any,
    modules: IfcModules,
    file_info: IfcFileInfo,
    unit_info: IfcUnitInfo,
) -> IfcSpaceGeometry:
    scale = unit_info.MetersPerLengthUnit
    info = _space_info(space, modules, scale)
    representation, solid = _find_supported_solid(space)
    profile = solid.SweptArea
    if not (
        profile.is_a("IfcArbitraryClosedProfileDef")
        or profile.is_a("IfcArbitraryProfileDefWithVoids")
    ):
        raise IfcGeometryUnsupported(
            "Поддерживается IfcArbitraryClosedProfileDef или "
            "IfcArbitraryProfileDefWithVoids; найден "
            f"{profile.is_a()}."
        )

    object_matrix = _matrix_to_lists(
        modules.placement.get_local_placement(
            space.ObjectPlacement
        )
    )
    solid_matrix = _matrix_to_lists(
        modules.placement.get_axis2placement(solid.Position)
    )
    combined_matrix = _matrix_multiply(
        object_matrix,
        solid_matrix,
    )

    outer = _parse_loop(
        profile.OuterCurve,
        solid_matrix,
        object_matrix,
        scale,
        is_outer=True,
    )
    inner_curves = list(
        getattr(profile, "InnerCurves", None) or []
    )
    holes = [
        _parse_loop(
            curve,
            solid_matrix,
            object_matrix,
            scale,
            is_outer=False,
        )
        for curve in inner_curves
    ]
    _validate_holes(outer, holes)

    depth = float(solid.Depth)
    if not math.isfinite(depth) or depth <= 0:
        raise IfcGeometryInvalid(
            f"Высота экструзии должна быть положительной; {depth}."
        )
    direction_values = [
        float(value)
        for value in solid.ExtrudedDirection.DirectionRatios
    ]
    direction = _normalize_vector(direction_values)
    world_axis = _normalize_vector(
        _transform_vector(combined_matrix, direction)
    )
    height_m = depth * scale

    analytic_area = (outer.AreaM2 or 0.0) - sum(
        hole.AreaM2 or 0.0
        for hole in holes
    )
    if not math.isfinite(analytic_area) or analytic_area <= 0:
        raise IfcGeometryInvalid(
            "Площадь профиля с учётом отверстий должна быть "
            "положительной."
        )
    perimeter = (outer.PerimeterM or 0.0) + sum(
        hole.PerimeterM or 0.0
        for hole in holes
    )

    vertex_count, triangle_count, triangulated_area = (
        _triangulation_check(
            model,
            space,
            modules,
            world_axis,
        )
    )
    triangulation_difference = (
        triangulated_area - analytic_area
    )
    allowed_difference = max(
        TRIANGULATION_AREA_ABSOLUTE_TOLERANCE_M2,
        analytic_area * TRIANGULATION_AREA_RELATIVE_TOLERANCE,
    )
    if abs(triangulation_difference) > allowed_difference:
        raise IfcGeometryInvalid(
            "Площадь аналитического профиля не совпадает с "
            "независимой триангуляцией: "
            f"analytic={analytic_area} м², "
            f"triangulated={triangulated_area} м², "
            f"delta={triangulation_difference} м²."
        )

    representation_info = IfcRepresentationInfo(
        Identifier=getattr(
            representation,
            "RepresentationIdentifier",
            None,
        ),
        Type=getattr(
            representation,
            "RepresentationType",
            None,
        ),
        SolidType=solid.is_a(),
        ProfileType=profile.is_a(),
        CurveType=profile.OuterCurve.is_a(),
        ExtrusionDirection=IfcPoint3D(
            X=direction[0],
            Y=direction[1],
            Z=direction[2],
        ),
        TriangulatedVertexCount=vertex_count,
        TriangulatedTriangleCount=triangle_count,
        TriangulatedAreaM2=triangulated_area,
        AnalyticAreaDifferenceM2=triangulation_difference,
    )

    diagnostics = [
        "Аналитический профиль прочитан до триангуляции.",
        "Вся цепочка IfcLocalPlacement разрешена.",
        "Площадь подтверждена независимой триангуляцией "
        f"(Δ={triangulation_difference:.12g} м²).",
    ]
    if outer.SourceHadRepeatedEndpoint:
        diagnostics.append(
            "Наружный профиль явно замкнут повтором первой точки."
        )
    else:
        diagnostics.append(
            "Наружный профиль логически замкнут семантикой "
            "IfcArbitraryClosedProfileDef."
        )

    return IfcSpaceGeometry(
        source=SOURCE_NAME,
        geometry_status="validated_candidate",
        IfcFile=file_info,
        IfcSpace=info,
        Units=unit_info,
        Representation=representation_info,
        LocalToWorldMatrix=_matrix_translation_to_meters(
            object_matrix,
            scale,
        ),
        MatrixLengthUnit="metre",
        OuterBoundaryLoop=outer,
        InnerBoundaryLoops=holes,
        AreaM2=analytic_area,
        PerimeterM=perimeter,
        HeightM=height_m,
        MatchStatus="pending",
        Diagnostics=diagnostics,
    )


def _saved_global_id(room: dict[str, Any]) -> str:
    geometry = room.get("IfcSpaceGeometry")
    if not isinstance(geometry, dict):
        return ""
    identity = geometry.get("IfcSpace")
    if not isinstance(identity, dict):
        return ""
    return _normalize_identifier(identity.get("GlobalId"))


def _area_differences(
    ifc_area: float,
    source_area: Any,
) -> tuple[float | None, float | None]:
    if source_area is None:
        return None, None
    try:
        area = float(source_area)
    except (TypeError, ValueError):
        return None, None
    if not math.isfinite(area):
        return None, None
    difference = ifc_area - area
    percentage = difference / area * 100.0 if area != 0 else None
    return difference, percentage


def _room_boundary_area(room: dict[str, Any]) -> Any:
    if room.get("BoundaryAreaM2") is not None:
        return room["BoundaryAreaM2"]
    boundary = room.get("Boundary")
    if isinstance(boundary, dict):
        return boundary.get("ContourAreaM2")
    return None


def _apply_room_context(
    geometry: IfcSpaceGeometry,
    room: dict[str, Any],
    method: str,
) -> IfcSpaceGeometry:
    result = geometry.model_copy(deep=True)
    result.MatchStatus = "matched"
    result.MatchMethod = method
    result.MatchedRoomCode = str(room.get("Code", ""))

    net_area = room.get("MagiCadNetAreaM2")
    if net_area is None:
        net_area = room.get("NetAreaM2")
    (
        result.NetAreaDifferenceM2,
        result.NetAreaDifferencePercent,
    ) = _area_differences(result.AreaM2 or 0.0, net_area)
    (
        result.BoundaryAreaDifferenceM2,
        result.BoundaryAreaDifferencePercent,
    ) = _area_differences(
        result.AreaM2 or 0.0,
        _room_boundary_area(room),
    )

    long_name = _normalize_identifier(
        result.IfcSpace.LongName
    )
    room_name = _normalize_identifier(room.get("Name"))
    if long_name and room_name and long_name != room_name:
        result.Warnings.append(
            "IfcSpace.LongName не совпадает с Room.Name после "
            "нормализации; сопоставление выполнено только по "
            f"{method}."
        )
    else:
        result.Diagnostics.append(
            "IfcSpace.LongName подтверждает Room.Name."
        )
    result.Diagnostics.append(
        f"Сопоставление с комнатой выполнено: {method}."
    )
    return result


def _read_rooms_document(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise IfcSpaceImportError(
            f"Не удалось прочитать rooms.json: {path}: {error}"
        ) from error
    if not isinstance(document, dict):
        raise IfcSpaceImportError(
            "Корень rooms.json должен быть JSON-объектом."
        )
    rooms = document.get("Rooms")
    if not isinstance(rooms, list):
        raise IfcSpaceImportError(
            "rooms.json должен содержать массив Rooms."
        )
    if not all(isinstance(room, dict) for room in rooms):
        raise IfcSpaceImportError(
            "Каждый элемент Rooms должен быть JSON-объектом."
        )
    return document


def analyze_ifc_spaces(
    ifc_path: str | Path,
    rooms_document: dict[str, Any],
    *,
    rooms_path_label: str = "<memory>",
    modules: IfcModules | None = None,
) -> IfcImportOutcome:
    ifc_file = Path(ifc_path).resolve()
    if not ifc_file.is_file():
        raise IfcSpaceImportError(
            f"IFC-файл не найден: {ifc_file}"
        )
    if not isinstance(rooms_document.get("Rooms"), list):
        raise IfcSpaceImportError(
            "rooms.json должен содержать массив Rooms."
        )

    loaded_modules = modules or _load_ifcopenshell()
    try:
        model = loaded_modules.root.open(str(ifc_file))
    except Exception as error:
        raise IfcSpaceImportError(
            f"Не удалось открыть IFC-файл {ifc_file}: {error}"
        ) from error

    schema = str(model.schema)
    file_info = IfcFileInfo(
        Path=str(ifc_file),
        Sha256=_sha256(ifc_file),
        Schema=schema,
    )
    unit_info = _read_units(model, loaded_modules)
    spaces = list(model.by_type("IfcSpace"))
    parsed_spaces: list[ParsedSpace] = []
    import_results: list[IfcSpaceImportResult] = []

    for space in spaces:
        info = _space_info(
            space,
            loaded_modules,
            unit_info.MetersPerLengthUnit,
        )
        try:
            geometry = _parse_space_geometry(
                model,
                space,
                loaded_modules,
                file_info,
                unit_info,
            )
            parsed_spaces.append(
                ParsedSpace(
                    entity=space,
                    info=info,
                    geometry=geometry,
                    geometry_status="validated_candidate",
                    diagnostics=[],
                )
            )
        except IfcGeometryUnsupported as error:
            parsed_spaces.append(
                ParsedSpace(
                    entity=space,
                    info=info,
                    geometry=None,
                    geometry_status="unsupported",
                    diagnostics=[str(error)],
                )
            )
        except IfcGeometryInvalid as error:
            parsed_spaces.append(
                ParsedSpace(
                    entity=space,
                    info=info,
                    geometry=None,
                    geometry_status="invalid",
                    diagnostics=[str(error)],
                )
            )
        except Exception as error:
            parsed_spaces.append(
                ParsedSpace(
                    entity=space,
                    info=info,
                    geometry=None,
                    geometry_status="invalid",
                    diagnostics=[
                        "Неожиданная ошибка чтения геометрии "
                        f"{type(error).__name__}: {error}"
                    ],
                )
            )

    rooms = rooms_document["Rooms"]
    proposals: list[MatchProposal] = []
    terminal_status: dict[int, tuple[str, list[str]]] = {}

    for parsed_index, parsed in enumerate(parsed_spaces):
        if parsed.geometry is None:
            terminal_status[parsed_index] = (
                parsed.geometry_status,
                parsed.diagnostics,
            )
            continue

        global_id = _normalize_identifier(parsed.info.GlobalId)
        global_matches = [
            index
            for index, room in enumerate(rooms)
            if _saved_global_id(room) == global_id
            and global_id
        ]
        if len(global_matches) == 1:
            proposals.append(
                MatchProposal(
                    parsed=parsed,
                    room_index=global_matches[0],
                    method="saved_global_id",
                )
            )
            continue
        if len(global_matches) > 1:
            terminal_status[parsed_index] = (
                "ambiguous",
                [
                    "Один GlobalId ранее сохранён у нескольких "
                    "комнат; автоматическое сопоставление запрещено."
                ],
            )
            continue

        normalized_name = _normalize_identifier(parsed.info.Name)
        code_matches = [
            index
            for index, room in enumerate(rooms)
            if _normalize_identifier(room.get("Code"))
            == normalized_name
            and normalized_name
        ]
        if len(code_matches) == 1:
            proposals.append(
                MatchProposal(
                    parsed=parsed,
                    room_index=code_matches[0],
                    method="normalized_name_to_room_code",
                )
            )
        elif len(code_matches) > 1:
            terminal_status[parsed_index] = (
                "ambiguous",
                [
                    "IfcSpace.Name совпадает с Room.Code у "
                    "нескольких комнат; нечёткое сопоставление "
                    "не применяется."
                ],
            )
        else:
            terminal_status[parsed_index] = (
                "unmatched",
                [
                    "Не найдено точного нормализованного "
                    "совпадения IfcSpace.Name и Room.Code."
                ],
            )


    proposals_by_room: dict[int, list[MatchProposal]] = {}
    for proposal in proposals:
        proposals_by_room.setdefault(
            proposal.room_index,
            [],
        ).append(proposal)

    accepted: list[MatchProposal] = []
    for room_index, room_proposals in proposals_by_room.items():
        global_proposals = [
            proposal
            for proposal in room_proposals
            if proposal.method == "saved_global_id"
        ]
        if len(global_proposals) == 1:
            accepted.append(global_proposals[0])
            for proposal in room_proposals:
                if proposal is global_proposals[0]:
                    continue
                parsed_index = parsed_spaces.index(proposal.parsed)
                terminal_status[parsed_index] = (
                    "ambiguous",
                    [
                        "Комната уже однозначно сопоставлена по "
                        "ранее сохранённому GlobalId."
                    ],
                )
            continue
        if len(room_proposals) == 1:
            accepted.append(room_proposals[0])
            continue
        for proposal in room_proposals:
            parsed_index = parsed_spaces.index(proposal.parsed)
            terminal_status[parsed_index] = (
                "ambiguous",
                [
                    "Несколько IfcSpace претендуют на одну комнату "
                    "по одинаковому Name; автоматический выбор "
                    "запрещён."
                ],
            )

    result_document = copy.deepcopy(rooms_document)
    result_rooms = result_document["Rooms"]
    matched_geometries: list[IfcSpaceGeometry] = []
    accepted_by_identity = {
        id(proposal.parsed): proposal
        for proposal in accepted
    }

    for parsed_index, parsed in enumerate(parsed_spaces):
        proposal = accepted_by_identity.get(id(parsed))
        if proposal is not None and parsed.geometry is not None:
            geometry = _apply_room_context(
                parsed.geometry,
                result_rooms[proposal.room_index],
                proposal.method,
            )
            result_rooms[proposal.room_index][
                "IfcSpaceGeometry"
            ] = geometry.model_dump(mode="json")
            matched_geometries.append(geometry)
            import_results.append(
                IfcSpaceImportResult(
                    GlobalId=parsed.info.GlobalId,
                    Name=parsed.info.Name,
                    LongName=parsed.info.LongName,
                    Status="matched",
                    MatchMethod=proposal.method,
                    MatchedRoomCode=geometry.MatchedRoomCode,
                    GeometryStatus=geometry.geometry_status,
                    Diagnostics=geometry.Diagnostics
                    + geometry.Warnings,
                )
            )
            continue

        status, diagnostics = terminal_status.get(
            parsed_index,
            (
                "ambiguous",
                ["Сопоставление не завершено однозначно."],
            ),
        )
        import_results.append(
            IfcSpaceImportResult(
                GlobalId=parsed.info.GlobalId,
                Name=parsed.info.Name,
                LongName=parsed.info.LongName,
                Status=status,
                GeometryStatus=parsed.geometry_status,
                Diagnostics=diagnostics,
            )
        )

    summary = IfcSpaceImportSummary(
        source=SOURCE_NAME,
        Mode="analysis",
        InputIfcPath=str(ifc_file),
        InputRoomsPath=rooms_path_label,
        IfcFileSha256=file_info.Sha256,
        IfcSchema=schema,
        FoundIfcSpaces=len(spaces),
        MatchedIfcSpaces=sum(
            result.Status == "matched"
            for result in import_results
        ),
        AmbiguousIfcSpaces=sum(
            result.Status == "ambiguous"
            for result in import_results
        ),
        UnmatchedIfcSpaces=sum(
            result.Status == "unmatched"
            for result in import_results
        ),
        UnsupportedIfcSpaces=sum(
            result.GeometryStatus == "unsupported"
            for result in import_results
        ),
        Results=import_results,
        Diagnostics=[
            "Исходный rooms.json и DWG не изменялись.",
            "Существующий Boundary не заменялся.",
            "Нечёткое сопоставление не применялось.",
        ],
    )
    result_document["IfcSpaceImport"] = summary.model_dump(
        mode="json"
    )
    return IfcImportOutcome(
        rooms_document=result_document,
        summary=summary,
        matched_geometries=matched_geometries,
    )


def run_import(
    ifc_path: str | Path,
    rooms_path: str | Path,
    *,
    output_path: str | Path | None = None,
    analyze_only: bool = False,
    overwrite: bool = False,
    modules: IfcModules | None = None,
) -> IfcImportOutcome:
    rooms_file = Path(rooms_path).resolve()
    if not rooms_file.is_file():
        raise IfcSpaceImportError(
            f"rooms.json не найден: {rooms_file}"
        )
    rooms_document = _read_rooms_document(rooms_file)
    outcome = analyze_ifc_spaces(
        ifc_path,
        rooms_document,
        rooms_path_label=str(rooms_file),
        modules=modules,
    )

    if analyze_only:
        if output_path is not None:
            raise IfcSpaceImportError(
                "В режиме --analyze путь --output не используется."
            )
        return outcome

    if output_path is None:
        raise IfcSpaceImportError(
            "Для записи результата укажите отдельный --output."
        )
    output_file = Path(output_path).resolve()
    if output_file == rooms_file:
        raise IfcSpaceImportError(
            "Исходный rooms.json нельзя перезаписывать. Укажите "
            "другой --output."
        )
    if output_file.exists() and not overwrite:
        raise IfcSpaceImportError(
            f"Файл результата уже существует: {output_file}. "
            "Используйте новый путь или явный --overwrite."
        )

    outcome.summary.Mode = "write"
    outcome.summary.OutputPath = str(output_file)
    outcome.rooms_document["IfcSpaceImport"] = (
        outcome.summary.model_dump(mode="json")
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(
            outcome.rooms_document,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return outcome


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only импорт геометрии MagiCAD Room IfcSpace "
            "в отдельный rooms.json."
        )
    )
    parser.add_argument(
        "--ifc",
        required=True,
        help="Путь к исходному IFC.",
    )
    parser.add_argument(
        "--rooms",
        required=True,
        help="Путь к существующему rooms.json.",
    )
    parser.add_argument(
        "--output",
        help="Новый путь результата; исходный rooms.json не меняется.",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Проверить и вывести результат без записи.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Явно разрешить замену существующего output-файла.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_argument_parser()
    arguments = parser.parse_args(argv)
    try:
        outcome = run_import(
            arguments.ifc,
            arguments.rooms,
            output_path=arguments.output,
            analyze_only=arguments.analyze,
            overwrite=arguments.overwrite,
        )
    except IfcSpaceImportError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    if arguments.analyze:
        payload = outcome.analysis_payload()
    else:
        payload = {
            "status": "ok",
            "output": outcome.summary.OutputPath,
            "IfcSpaceImport": outcome.summary.model_dump(
                mode="json"
            ),
        }
    print(
        json.dumps(payload, ensure_ascii=False, indent=2)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
