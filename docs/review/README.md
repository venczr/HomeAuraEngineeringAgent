# HomeAura: пакет архитектурного аудита

## Дополнение R4 — Г-комната и двери

[Результат](HOMEAURA_COMPLEX_ROOMS_RESULT.md) · [Схема](complex-rooms/complex-comparison.png). Два независимых BODY в Г-форме и отдельная дверная пара проверены; общего соединения с коллектором пока нет. 13 сценариев выполнены. Актуальный общий архив: HOMEAURA_AUDIT_PACKAGE_R4.zip.

## Текущая версия R3

1. [Результат M1a и малого M1b](HOMEAURA_M1A_M1B_RESULT.md): BUILD ограниченного rectangle,17+5 тестов, independent review, явные границы.
2. [M2 preflight](HOMEAURA_M2_PREFLIGHT.md): max200 и точный p100/R80 разворот; полной принятой раскладки M2 нет.
3. [Воспроизведение](m1a-v2/REPRODUCE.md), [сравнение вариантов](m1a-v2/comparison.png), [эксперименты M2](m2-preflight/preflight.png).

Архив актуальной версии: HOMEAURA_AUDIT_PACKAGE_R3.zip. Исторические R1/R2 сохраняются; статусы ниже относятся к предыдущим прогонам. Изменены только документы/изолированный стенд,608 исходных файлов продукта сверены без изменений. Claude-аудит не состоялся: expired OAuth. CAD export запрещён.

Рабочая копия: `C:\AI\HomeAuraEngineeringAgent`, HEAD `9e86e06` плюс незакоммиченные изменения на момент анализа.

1. [Архитектура и приоритетные дефекты](HOMEAURA_ARCHITECTURE_AUDIT.md)
2. [Внешние алгоритмы, source research и лицензии](HOMEAURA_GRAIL_RESEARCH.md)
3. [Build / Adapt / Reuse matrix](HOMEAURA_BUILD_ADAPT_REUSE_MATRIX.md)
4. [Спецификация Floor Engine 2.0](HOMEAURA_FLOOR_ENGINE_V2.md)
5. [Тестовая стратегия и C05/C06](HOMEAURA_TEST_STRATEGY.md)
6. [Миграция, один POC и ответы на 20 вопросов](HOMEAURA_MIGRATION_PLAN.md)

В `evidence/` — file/source inventory, hashes, Python import edges, перечень 832 файлов-кандидатов с текстовыми совпадениями C05/C06 (широкий поиск также может совпадать с hex hashes), извлечённые D178 координаты и воспроизводимый sampling counterexample. Исходники продукта не изменены. Изолированный M1a выполнен частично; migration и полный solver POC не выполнены.

Проверки: 30 Python tests и 57/57 native harness PASS; отдельно воспроизведён пропуск 20-мм препятствия legacy helper. Прохождение старых tests не означает корректность всех generated routes.

Границы: HeatGrid attachment 403; полный HLA paper/source не получен; коммерческие engines не запускались на fixtures; все DWG/PDF и исторические временные файлы не прошли построчную/визуальную экспертизу. Эти ограничения подробно отражены в отчётах, а не скрыты за заявлением о полной сертификации.

## Ревизия по критическому разбору

[M1a UFH Designer benchmark](HOMEAURA_M1A_UFH_DESIGNER_BENCHMARK.md): прямой результат FAIL; ADAPT/BUILD не установлен из-за неполноты checker. В `m1a/` — фиксированный вход, исходный архив UFH, runner, checker, 6 мутаций, результаты, SVG, зависимости и журнал 81 upstream-теста (76 passed / 5 failed). Полного положительного bifilar solver fixture пока нет.
