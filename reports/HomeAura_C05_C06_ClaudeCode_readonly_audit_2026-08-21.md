# Claude Code Opus — независимый read-only аудит C05/C06

Дата: 2026-08-21  
Режим: `claude --model opus --effort max`, только чтение.  
Объект: официальный `HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185` (D185).  
Итог Claude Code: **CURRENT_OFFICIAL NO-GO**.

## Проверенные источники

- `reports/HomeAura_owner_floor_heating_routing_rules_for_all_helpers_2026-08-20.md`
- `reports/HomeAura_C05_C06_browser_helpers_message_2026-08-20.md`
- `homeaura-native-editor/examples/proposals/HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185/HomeAura_TwoFloor_C12BoundedTerminal_D185.homeaura.json`
- `homeaura-native-editor/examples/proposals/HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185/engineering_diagnostics.json`
- `homeaura-native-editor/examples/proposals/HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185/HomeAura_Floor1_D185_Clean_View.png`
- `tmp/chatgpt_c05c06_solver_20260820/chatgpt_layered_top.diagnostic.png`

Регламент уже содержит page-by-page факты двух owner PDF. Claude не принимал готовые claims и пересчитывал факты из `ordered_points`, стен и `vertical_transitions`.

## Owner-morphology checklist

| Требование | C05 | C06 |
|---|---:|---:|
| Основное BODY — bifilar/counterflow улитка | FAIL | FAIL |
| Змейка только как локальный остаточный добор | FAIL | FAIL |
| 3×100 у наружной стены без прямого U | частично | частично |
| Центр доведён до геометрического предела | PASS | PASS |
| R80 и не менее 160 мм касательной между поворотами | FAIL | FAIL |
| Каждая смена Z — материализованный S_BEND_R80 вне стены | FAIL | FAIL |
| Стена пересекается только через проверенный проём/гильзу | FAIL | FAIL |
| BODY внутри назначенного домена | PASS | PASS |
| Нет недоказанных пересечений/продольных наложений | FAIL | FAIL |
| Пучок упорядочен, не более трёх осей ×100 в одном слое | PASS | PASS |
| Физическая непрерывность до точных Eurocone | FAIL | FAIL |
| Длина 40–80 м и разброс пары не более 2 м | PASS | PASS |
| Белые зоны только по explicit verified exclusion | не доказано | не доказано |

## Точные дефекты, установленные Claude Code

1. **Доминирующая змейка вместо улитки.** C05 P11–P36: 13 проходов, C06 P6–P31: 12 проходов. Около 67% прямоугольной котельной заполнено последовательной змейкой, а не противоточной bifilar-морфологией.
2. **S-bend внутри стенового солида.** C05 transition segments 0, 3, 5, 8, 10 и C06 segments 0, 3, 5 попадают в W024/W025/W026. Восемь из десяти Z-переходов меняют высоту в стене.
3. **Нет требуемой касательной между S-bend и плановым R80.** C06 segment 31 оставляет 0 мм; C05 segment 36 оставляет примерно 65,5 мм при требовании не менее 160 мм.
4. **Проходы стен не имеют физического входного доказательства.** Диагностика даёт C05=7 и C06=5 TRANSIT-wall intersections, но typed openings/doors/sleeves отсутствуют; `sleeves_added=false`.
5. **Часть транзита идёт вне назначенной территории.** C05 P4→P5 и C06 P4→P5 лежат в R03, а не R04.
6. **Продольная суперпозиция.** C06 segment 32 коллинеарно перекрывает C05 segment 1 примерно на 1900 мм при ΔZ=38; точечный stack-check не доказывает безопасность длинного совместного участка.
7. **Near-collector tolerance ошибочно выглядит как подключение.** Терминальные зазоры до портов 8–11 составляют примерно 539/790/599/675 мм. `start/end_at_collector=true` возникает из tolerance 4100 мм; физические Eurocone tails отсутствуют, `collectorContinuous=0`.
8. **Raw 3×100 не проходит.** Для обоих контуров `exterior3x100_pass=false`; useful-span опирается на константный corner envelope, а не на полный доказанный физический R80-envelope.
9. **Минимальный межконтурный запас относится к этой паре.** C05 segment 37 проходит над множеством C06 BODY-линий при ΔZ=27, давая лишь 11 мм поверхностного зазора.
10. **Домен/исключения не авторитетны.** Для R04 расходятся 14,4/15,9/16,83 м²; verified exclusions оборудования котельной отсутствуют. Кухонные или мебельные пустоты из owner PDF переносить запрещено.

## Обязательные данные от Kimi

1. Авторитетный finish-face полигон R04 и разрешение расхождения площадей.
2. Реестр каждого физического проёма/гильзы: координаты, ширина/диаметр и допустимое Z-окно.
3. Явные verified exclusions оборудования либо подтверждение их отсутствия; кухня/мебель не являются автоматическим exclusion.
4. Точные мировые XYZ Eurocone K1 портов 8/9/10/11 и направление выхода.
5. Полная геометрия соседних C02/C04/C07 в зоне 300 мм.
6. Статус полосы y=12100..12300 в R03.
7. Решение владельца о допустимости ΔZ=27 против 38 мм.
8. Доказанные слои пола для легальности z=70 под BODY z=108.
9. Полные ordered Point3, BODY/TRANSIT ranges и каждый S_BEND_R80 с индексами, касательными, радиусом и samples.
10. Воспроизводимые native-метрики coverage, max-gap, contacts, wall/turn-wall, R80, длины и spread; без hidden length и без ложного Eurocone/installation claim.

## Итог

`CURRENT_OFFICIAL=NO-GO`. Блокирующие классы: неверная BODY-морфология, переходы высоты внутри стен, дефицит R80-касательных, проходы без проверенных отверстий/гильз и отсутствие Eurocone-непрерывности. Требуется перепроектирование C05/C06, а не косметическая правка.

Данный файл — контрольная матрица для последующего независимого аудита ответа Kimi. Он не является новой геометрией и ничего не публикует.
