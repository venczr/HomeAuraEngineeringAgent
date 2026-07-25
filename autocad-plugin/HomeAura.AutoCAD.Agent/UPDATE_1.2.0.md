# HomeAura AutoCAD Agent 1.2.0

Версии:

- AutoCAD-плагин: `1.2.0.0`;
- HomeAura API: `0.6.0`;
- формат `rooms.json`: `1.1`.

## Что добавлено

- контракт `Boundary` с вершинами XYZ, bulge и типом сегмента;
- точные площадь и периметр из AutoCAD `Polyline`;
- нормализация дубликатов, замыкания и направления;
- проверка самопересечений;
- point-in-polygon с поддержкой дуг;
- выбор минимального содержащего контура;
- диагностика неподдерживаемых типов;
- read-only команда `HA_DISCOVER_ROOM_BOUNDARIES`;
- обратное чтение `rooms.json` формата `1.0`.

## Проверка

1. Загрузить временно собранную DLL через `NETLOAD`.
2. Выполнить `HA_STATUS` и проверить версию `1.2.0.0`.
3. Выполнить `HA_API_STATUS` и проверить API `0.6.0`.
4. Выполнить `HA_DISCOVER_ROOM_BOUNDARIES`.
5. Только при наличии валидной замкнутой `LWPOLYLINE` выполнить
   `HA_EXPORT_ROOMS`.
6. Проверить `Boundary`, `ContourAreaM2`, `PerimeterM` и диагностику
   в созданном `rooms.json`.
