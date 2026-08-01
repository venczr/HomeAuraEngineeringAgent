from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NoReturn

from pydantic import BaseModel, ConfigDict, Field, ValidationError


MAX_SNAPSHOT_COUNT = 2_147_483_647


def reject_non_finite_json_constant(value: str) -> NoReturn:
    raise ValueError(
        f"JSON содержит недопустимое числовое значение: {value}"
    )


class _FiniteSnapshotModel(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        allow_inf_nan=False,
    )


class PointSnapshot(_FiniteSnapshotModel):

    X: float = 0.0
    Y: float = 0.0
    Z: float = 0.0


class ExtentsSnapshot(_FiniteSnapshotModel):

    Minimum: PointSnapshot
    Maximum: PointSnapshot


class LayerSnapshot(_FiniteSnapshotModel):

    Name: str
    IsOff: bool = False
    IsFrozen: bool = False
    IsLocked: bool = False
    ColorIndex: int = 0


class EntityTypeSnapshot(_FiniteSnapshotModel):

    DxfName: str = "UNKNOWN"
    RxClassName: str = "UNKNOWN"
    DotNetType: str = "UNKNOWN"
    Count: int = Field(
        default=0,
        ge=0,
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
    IsAnonymous: bool = False
    IsExternalReference: bool = False


class ModelSnapshot(_FiniteSnapshotModel):

    GeneratedAtUtc: str
    DrawingName: str
    DrawingFullPath: str
    AcadVersion: str
    PluginVersion: str
    Is64BitProcess: bool
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


def load_snapshot(path: Path) -> ModelSnapshot:
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")

    if not path.is_file():
        raise ValueError(f"Указанный путь не является файлом: {path}")

    try:
        text = path.read_text(encoding="utf-8-sig")
        raw_data = json.loads(
            text,
            parse_constant=reject_non_finite_json_constant,
        )
    except UnicodeDecodeError as exc:
        raise ValueError(f"Не удалось прочитать кодировку JSON: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Некорректный JSON, строка {exc.lineno}, "
            f"столбец {exc.colno}: {exc.msg}"
        ) from exc

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
