from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import NoReturn

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)


MAX_SNAPSHOT_COUNT = 2_147_483_647
MIN_LAYER_COLOR_INDEX = -32_768
MAX_LAYER_COLOR_INDEX = 32_767
DUPLICATE_JSON_KEY_MESSAGE = "JSON содержит повторяющиеся ключи."
JSON_NESTING_TOO_DEEP_MESSAGE = "JSON имеет слишком глубокую вложенность."
EXTENTS_SPAN_NON_FINITE_MESSAGE = (
    "Габариты снимка выходят за конечный числовой диапазон."
)
ENTITY_TYPE_TOTAL_MISMATCH_MESSAGE = (
    "Сумма количеств типов объектов не совпадает с общим количеством "
    "объектов модели."
)


def reject_non_finite_json_constant(value: str) -> NoReturn:
    raise ValueError(
        f"JSON содержит недопустимое числовое значение: {value}"
    )


def reject_duplicate_json_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(DUPLICATE_JSON_KEY_MESSAGE)
        result[key] = value
    return result


class _FiniteSnapshotModel(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        allow_inf_nan=False,
    )


class PointSnapshot(_FiniteSnapshotModel):

    X: float = Field(default=0.0, strict=True)
    Y: float = Field(default=0.0, strict=True)
    Z: float = Field(default=0.0, strict=True)


class ExtentsSnapshot(_FiniteSnapshotModel):

    Minimum: PointSnapshot
    Maximum: PointSnapshot

    @model_validator(mode="after")
    def require_finite_spans(self) -> ExtentsSnapshot:
        spans = (
            self.Maximum.X - self.Minimum.X,
            self.Maximum.Y - self.Minimum.Y,
            self.Maximum.Z - self.Minimum.Z,
        )
        if not all(math.isfinite(span) for span in spans):
            raise ValueError(EXTENTS_SPAN_NON_FINITE_MESSAGE)
        return self


class LayerSnapshot(_FiniteSnapshotModel):

    Name: str
    IsOff: bool = Field(default=False, strict=True)
    IsFrozen: bool = Field(default=False, strict=True)
    IsLocked: bool = Field(default=False, strict=True)
    ColorIndex: int = Field(
        default=0,
        ge=MIN_LAYER_COLOR_INDEX,
        le=MAX_LAYER_COLOR_INDEX,
        strict=True,
    )


class EntityTypeSnapshot(_FiniteSnapshotModel):

    model_config = ConfigDict(
        extra="ignore",
        allow_inf_nan=False,
        validate_default=True,
    )

    DxfName: str = "UNKNOWN"
    RxClassName: str = "UNKNOWN"
    DotNetType: str = "UNKNOWN"
    Count: int = Field(
        default=0,
        ge=1,
        le=MAX_SNAPSHOT_COUNT,
        strict=True,
    )


class BlockSnapshot(_FiniteSnapshotModel):

    Name: str
    EntityCount: int = Field(
        default=0,
        ge=0,
        le=MAX_SNAPSHOT_COUNT,
        strict=True,
    )
    IsAnonymous: bool = Field(default=False, strict=True)
    IsExternalReference: bool = Field(
        default=False,
        strict=True,
    )


class ModelSnapshot(_FiniteSnapshotModel):

    GeneratedAtUtc: str
    DrawingName: str
    DrawingFullPath: str
    AcadVersion: str
    PluginVersion: str
    Is64BitProcess: bool = Field(strict=True)
    DrawingUnits: str
    Extents: ExtentsSnapshot
    ModelSpaceEntityCount: int = Field(
        ge=0,
        le=MAX_SNAPSHOT_COUNT,
        strict=True,
    )
    Layers: list[LayerSnapshot]
    EntityTypes: list[EntityTypeSnapshot]
    BlockDefinitions: list[BlockSnapshot]

    @model_validator(mode="after")
    def require_entity_type_total(self) -> ModelSnapshot:
        entity_type_total = sum(
            entity_type.Count for entity_type in self.EntityTypes
        )
        if entity_type_total != self.ModelSpaceEntityCount:
            raise ValueError(ENTITY_TYPE_TOTAL_MISMATCH_MESSAGE)
        return self


def load_snapshot(path: Path) -> ModelSnapshot:
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")

    if not path.is_file():
        raise ValueError(f"Указанный путь не является файлом: {path}")

    try:
        text = path.read_text(encoding="utf-8-sig")
        raw_data = json.loads(
            text,
            object_pairs_hook=reject_duplicate_json_keys,
            parse_constant=reject_non_finite_json_constant,
        )
    except UnicodeDecodeError as exc:
        raise ValueError(f"Не удалось прочитать кодировку JSON: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Некорректный JSON, строка {exc.lineno}, "
            f"столбец {exc.colno}: {exc.msg}"
        ) from exc
    except RecursionError as exc:
        raise ValueError(JSON_NESTING_TOO_DEEP_MESSAGE) from exc

    try:
        return ModelSnapshot.model_validate(raw_data)
    except ValidationError as exc:
        raise ValueError(
            "Структура JSON не соответствует формату HomeAura:\n"
            f"{exc}"
        ) from exc


def detect_engineering_objects(
    snapshot: ModelSnapshot,
) -> list[EntityTypeSnapshot]:
    keywords = (
        "MAGI",
        "MAGICAD",
        "MC_",
        "MEP",
        "DUCT",
        "PIPE",
        "SPACE",
        "ROOM",
        "WINDOW",
        "WALL",
    )

    result: list[EntityTypeSnapshot] = []

    for entity in snapshot.EntityTypes:
        searchable_text = " ".join(
            (
                entity.DxfName,
                entity.RxClassName,
                entity.DotNetType,
            )
        ).upper()

        if any(keyword in searchable_text for keyword in keywords):
            result.append(entity)

    return result


def print_summary(snapshot: ModelSnapshot) -> None:
    minimum = snapshot.Extents.Minimum
    maximum = snapshot.Extents.Maximum

    size_x = maximum.X - minimum.X
    size_y = maximum.Y - minimum.Y
    size_z = maximum.Z - minimum.Z

    print()
    print("=" * 62)
    print(" HomeAura Engineering Agent — снимок модели")
    print("=" * 62)
    print(f"Чертёж:              {snapshot.DrawingName}")
    print(f"Полный путь:         {snapshot.DrawingFullPath}")
    print(f"AutoCAD:             {snapshot.AcadVersion}")
    print(f"Версия плагина:      {snapshot.PluginVersion}")
    print(f"64-битный процесс:   {snapshot.Is64BitProcess}")
    print(f"Единицы DWG:         {snapshot.DrawingUnits}")
    print(f"Объектов в модели:   {snapshot.ModelSpaceEntityCount}")
    print(f"Слоёв:               {len(snapshot.Layers)}")
    print(f"Типов объектов:      {len(snapshot.EntityTypes)}")
    print(f"Определений блоков:  {len(snapshot.BlockDefinitions)}")
    print()
    print("Габариты модели:")
    print(f"  X: {size_x:.3f}")
    print(f"  Y: {size_y:.3f}")
    print(f"  Z: {size_z:.3f}")

    print()
    print("Основные типы объектов:")

    top_types = sorted(
        snapshot.EntityTypes,
        key=lambda item: item.Count,
        reverse=True,
    )[:15]

    if not top_types:
        print("  В пространстве модели объекты не обнаружены.")
    else:
        for entity in top_types:
            print(
                f"  {entity.Count:>5}  "
                f"{entity.DxfName:<20} "
                f"{entity.RxClassName}"
            )

    engineering_objects = detect_engineering_objects(snapshot)

    print()
    print("Вероятные архитектурные/инженерные объекты:")

    if not engineering_objects:
        print("  По названиям runtime-классов объекты не определены.")
    else:
        for entity in engineering_objects:
            print(
                f"  {entity.Count:>5}  "
                f"{entity.DxfName} | "
                f"{entity.RxClassName} | "
                f"{entity.DotNetType}"
            )

    print("=" * 62)
    print()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Чтение JSON-снимка модели AutoCAD."
    )
    parser.add_argument(
        "snapshot",
        type=Path,
        help="Путь к файлу model_snapshot.json",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        snapshot = load_snapshot(arguments.snapshot)
        print_summary(snapshot)
        return 0
    except (FileNotFoundError, ValueError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
