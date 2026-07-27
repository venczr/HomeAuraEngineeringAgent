# Read-only импорт геометрии IfcSpace

Модуль `agent.ifc_space_importer` добавляет к существующей комнате
необязательное поле `IfcSpaceGeometry`. Он не изменяет DWG, не запускает
IFC Export и не заменяет существующий `Boundary`.

## Опциональная зависимость

Основной API не импортирует IfcOpenShell. Для IFC-функции зависимость
устанавливается отдельно:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ifc.txt
```

Проверенная версия — `ifcopenshell==0.8.5`. Если пакет отсутствует,
основной FastAPI продолжает запускаться, а CLI IFC-импорта возвращает
понятную диагностическую ошибку с командой установки.

## Поддерживаемая геометрия

Текущий точный путь чтения:

```text
IfcExtrudedAreaSolid
└── IfcArbitraryClosedProfileDef
    └── IfcIndexedPolyCurve
        └── IfcCartesianPointList2D
```

Для отверстий также поддерживается
`IfcArbitraryProfileDefWithVoids` с теми же
`IfcIndexedPolyCurve`.

Импортёр:

- учитывает `IfcUnitAssignment`;
- разрешает полную цепочку `IfcLocalPlacement`;
- сохраняет исходные, локальные и мировые XYZ;
- `SourceVertices` остаются в исходной единице IFC, а `LocalVertices`,
  `WorldVertices` и матрица преобразования выдаются в метрах;
- проверяет минимум три различные вершины;
- удаляет только последовательные дубликаты;
- распознаёт явное и логическое замыкание;
- проверяет самопересечения и планарность;
- нормализует наружный loop в CCW, внутренние loops — в CW;
- вычисляет аналитическую площадь, периметр и высоту;
- независимо сверяет площадь с триангуляцией IfcOpenShell.

Неподдерживаемое представление не аппроксимируется: результат получает
`GeometryStatus = unsupported` и точное описание найденных IFC-типов.

## Сопоставление с rooms.json

Порядок строгий:

1. ранее сохранённый `IfcSpace.GlobalId`;
2. точное нормализованное совпадение `IfcSpace.Name` и `Room.Code`.

`IfcSpace.LongName` используется только как дополнительная проверка
`Room.Name`. Нечёткое сопоставление не применяется. Несколько
кандидатов дают `ambiguous`, отсутствие совпадения — `unmatched`.

## Режим анализа

Ничего не записывает:

```powershell
.\.venv\Scripts\python.exe -m agent.ifc_space_importer `
  --analyze `
  --ifc "C:\path\rooms.ifc" `
  --rooms "C:\path\rooms.json"
```

## Создание отдельного результата

```powershell
.\.venv\Scripts\python.exe -m agent.ifc_space_importer `
  --ifc "C:\path\rooms.ifc" `
  --rooms "C:\path\rooms.json" `
  --output "C:\path\rooms.with-ifc.json"
```

CLI запрещает использовать исходный `rooms.json` как `--output`.
Существующий результат также не заменяется без явного `--overwrite`.

## Контракт IfcSpaceGeometry

| Поле | Назначение |
|---|---|
| `source` | Всегда `MagiCADRoomIfcSpace` |
| `geometry_status` | Для прошедшего проверки тела — `validated_candidate` |
| `IfcFile` | Путь, SHA-256 и схема IFC |
| `IfcSpace` | STEP id, GlobalId, Name, LongName, ObjectType, PredefinedType и этаж |
| `Units` | Исходные единицы IFC и коэффициент длины в метры |
| `Representation` | Типы представления, профиля и кривой, результат триангуляции |
| `LocalToWorldMatrix` | Полностью разрешённое размещение IfcSpace; трансляция в метрах |
| `OuterBoundaryLoop` | Исходные, локальные и мировые XYZ наружного контура |
| `InnerBoundaryLoops` | Отверстия с исходными, локальными и мировыми XYZ |
| `AreaM2` | Площадь аналитического профиля с вычетом отверстий |
| `PerimeterM` | Наружный периметр плюс периметры отверстий |
| `HeightM` | Глубина `IfcExtrudedAreaSolid` в метрах |
| `MatchStatus` / `MatchMethod` | Статус и строгий способ сопоставления |
| `NetAreaDifference*` | `IfcSpace.AreaM2 - MagiCAD NetAreaM2` |
| `BoundaryAreaDifference*` | `IfcSpace.AreaM2 - текущий BoundaryAreaM2` |
| `Warnings` / `Diagnostics` | Предупреждения и доказательства проверок |

Поле добавляется к комнате без изменения её текущего `Boundary`.
Сводка операции сохраняется отдельно в `IfcSpaceImport`.

## Проверка Test_01

Для помещения 101:

- `GlobalId`: `3Vmsu$eoz6VAzSuuOWXaVz`;
- площадь: `17.321458459647975 м²`;
- периметр: `16.76796776 м`;
- высота: `2.8 м`;
- наружных loops: 1;
- отверстий: 0;
- отличие от `NetAreaM2`: около `+0.089997888359 м²`,
  или `+0.522288%`;
- `geometry_status`: `validated_candidate`.

`Boundary 101DA95` остаётся `provisional` и не заменяется.
