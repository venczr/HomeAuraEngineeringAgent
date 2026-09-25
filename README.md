# HomeAura Engineering Agent

Локальный AI-агент для автоматизации проектирования инженерных систем.

Основная рабочая связка:

- AutoCAD MEP 2024
- MagiCAD 2024 UR-2
- Python 3.12
- OpenAI Agents SDK
- C# / AutoCAD .NET API

Текущие версии:

- AutoCAD-плагин: `1.2.0.0`;
- Python API: `0.6.0`;
- формат помещений: `1.1`.

Документация:

- [геометрия помещений](docs/ROOM_GEOMETRY.md);
- [read-only импорт IfcSpace](docs/IFC_SPACE_IMPORT.md);
- [совместимость компонентов](docs/COMPATIBILITY.md);
- [пример rooms.json](docs/examples/rooms.v1.1.example.json).

Основная read-only команда диагностики в AutoCAD:
`HA_DISCOVER_ROOM_BOUNDARIES`.
