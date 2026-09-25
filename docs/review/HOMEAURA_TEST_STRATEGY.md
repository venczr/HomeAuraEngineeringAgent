# HomeAura: стратегия тестирования Floor Engine

## Текущий результат R3 — M1a / ограниченный M1b / M2 preflight

**Для малого синтетического rectangle выбран BUILD.** Ручной бифилярный эталон проходит независимый checker в явно ограниченной грамматике прямых и BOX-зон переходов. Исходные концы и численные пределы M1a не изменены. 17 тестов checker и 5 тестов шаблона прошли; поддержанная высота3000 мм, ширина4000..5000 мм, p200/Rmin80, фактический R100. Каждый кандидат проверяется, export всегда false. Не считать этот результат owner max-gap200 или постоянным offset200 на всех дугах.

У UFH Designer сохранены реальные параметры23 дуг без изменения исходных точек. Прямая замена и выбранная попытка терминального адаптера не прошли контракт; последняя наложила обратку на существующий проход. Это не доказательство невозможности иных адаптаций. Полный результат и границы: [M1a/M1b](HOMEAURA_M1A_M1B_RESULT.md).

Начат [M2 preflight](HOMEAURA_M2_PREFLIGHT.md): max200 достигнут отдельным физическим вариантом, но с недопустимыми для прежнего контракта20-мм участками; вариант не принят. Изолированный p100/R80 разворот из3 дуг проверен с точным free-space envelope. M2 целиком не закрыт. Claude review не состоялся из-за expired OAuth; production/CAD не менялись.

Предыдущие состояния R2 и первоначальные рекомендации ниже сохранены как история; при расхождении текущий статус задают эти два отчёта.

## Историческое состояние R2 — 9 сентября 2026

Текущий порядок: воспроизводимый контракт → независимый checker → benchmark UFH Designer → решение ADAPT/BUILD → один p200/R80 шаблон при необходимости → интеграция. Архитектура ниже является целевой, а не объёмом первого эксперимента. M1a и M1b разделены; 100/200 и C05/C06 относятся к M2.

UFH Designer закреплён на `bafc690f340943f6e04f9bf9a34b2c1e268d39e0` (Apache-2.0). Выполнен изолированный прогон: прямой выход не проходит фиксированные концы, направления и геометрическое покрытие. Upstream: 76/81 tests passed. **ADAPT/BUILD пока не установлен: checker не проверяет бифилярную морфологию, шаг и полный OD-clearance.** Ручная змейка проходит лишь реализованный геометрический набор; все шесть мутаций отклонены. Это не положительный solver fixture. Подробности и воспроизведение: [M1a benchmark](HOMEAURA_M1A_UFH_DESIGNER_BENCHMARK.md).

Уточнения обязательны для чтения остальной спецификации:

- `ProvenInfeasible` требует проверяемого необходимого условия либо исчерпания **полной явно заявленной модели**. Исчерпание каталога шаблонов даёт `NoFeasibleCandidateFound`/`Unsupported`.
- Любая обязательная проверка `Indeterminate` даёт общий `ValidationIndeterminate` и `export_allowed=false`; известный Fail сохраняет общий Fail. PASS требует Pass всех обязательных правил.
- RECT-01: 4000×3000 мм, p200/R80, OD16, surface wall clearance80, length≤80 м; до запуска фиксируются два BODY-конца и касательные. Геометрическое покрытие радиусом250 мм ≥99%, максимум расстояния до оси ≤250 мм. Отдельно обязательны шаг по самой кривой и even-in/odd-out с единственным центральным соединением. Это синтетические диагностические пороги, не теплотехнический расчёт; Valid golden пока отсутствует.
- holes=Unsupported у генератора не отменяет obstacle-negative тестов checker. p100 с прямой полуокружностью означает R50; иная топология при R80 требует построения и проверки реального свободного места, а не обещания «двух поворотов».
- Digest проверяет соответствие байтам/данным, не подлинность или инженерную истинность. На границе экспорта нужна независимая геометрическая проверка.
- Экономия 40–65% не измерена. Source hashes не заменяют snapshot содержимого незакоммиченного HomeAura. Приложенный архив UFH восстанавливает только закреплённый внешний эксперимент; полный M0 snapshot остаётся отдельной работой.

## Текущее состояние

FACT: 30 выбранных Python tests прошли (`test_floor_heating_engine.py`, `test_floor_heating_models.py`, `test_floor_heating_grid_layout.py`). Native console harness прошёл 57/57 через `dotnet run --project homeaura-native-editor-tests/HomeAura.NativeEditor.Tests.csproj --no-restore`. AutoCAD не требовался.

`RoomGeometry.Tests.csproj` — отдельный net48 console harness с linked source из plugin, без Autodesk assembly references. Native harness — console Exe, ProjectReference на net9.0-windows Windows Forms application. Значит, «без AutoCAD» уже частично достигнуто, но переносимый `dotnet test` geometry suite ещё предстоит создать. Не считать успешный build или пустой `dotnet test` тестовым прогоном: проверять обнаруженное количество tests.

Сильные стороны существующих тестов: отрицательные примеры пересечений и R80, неизменность геометрии соседних контуров, explicit Point3 transitions, source hashes, distinction BODY/TRANSIT, provenance и deferred inputs. Слабость: значительная часть закрепляет конкретные D-артефакты и метрики прежней спецификации; это не проверяет общий параметрический solver и не доказывает полноту coverage.

## Воспроизводимый дефект

`evidence/reproduce_sampling_gap.py` импортирует существующий `_allowed_segment`. Отрезок `(100,500)→(900,500)` пересекает hole `[(140,450),(160,450),(160,550),(140,550),(140,450)]`. Checker возвращает `True`, потому что проверяет x=100,200,… и пропускает препятствие между samples.

Это минимальная проверка helper, не полный публичный request. После исправления должны появиться два теста: прямой invariant geometry test и end-to-end request fixture на допустимых API параметрах. Тест должен подтверждать отклонение пересечения, а не конкретную библиотечную функцию.

## Уровни тестов

| Уровень | Что проверяет | Где запускать |
|---|---|---|
| Unit geometry | line/arc predicates, offsets wrappers, normalization, unit conversion | `dotnet test`, без CAD и UI |
| Solver contract | Supported/unsupported, deterministic candidates, exact terminals | То же |
| Property/invariant | Много параметров, transformations, boundary cases | То же; фиксированный seed и shrink |
| Golden replay | JSON input → measured invariants + canonical geometry | То же |
| Independent checker | Не доверяет generator metadata; проверяет final curves | Отдельная test assembly |
| API contract | DTO version, NaN/Inf, missing inputs, digest binding | Python/API tests, без CAD |
| Adapter integration | UCS/WCS, units, line/arc round-trip, rollback, ownership | AutoCAD/accoreconsole на копии DWG |
| BIM adapter | IFC placements/units/holes/GlobalId; Revit connector conversion | IFC offline; Revit отдельный integration job |
| Visual QA | CAD/SVG соответствует physical curves и статусу | Golden render, не инженерный oracle |

## Canonical fixtures

| ID | Вход/сценарий | Обязательный ожидаемый результат |
|---|---|---|
| RECT-01 | 4000×3000 mm, p200/R80, OD16, wall surface clearance80, length≤80m, заранее фиксированные terminals/tangents | Valid только после полного checker: coverage≥99% при radius250, max distance≤250mm, шаг по кривой, even-in/odd-out; golden ещё не принят |
| RECT-02 | Тот же rectangle с фиксированными supply/return и направлениями | Valid для заранее доказанного template; недоступные terminals — отказ |
| RECT-EDGE-100-200 | Южная wall face; axes100/200/300, затем 500/700; R80 | Три проверяемых edge rows; без direct U100 и pitch300 |
| RECT-EDGE-CORNER | Южная+восточная wall, разные spans/window projection | Согласованный угол или честный отказ |
| L-ROOM | Orthogonal L с известными openings | До реализации decomposition — Unsupported; позже проверенный combined layout |
| T-ROOM | T-shape с узкой шейкой | Проверка corridor capacity, не просто заполнение трёх rectangle |
| CONCAVE-ROOM | Concave polygon, узкий карман | Cells + residual policy или отказ |
| ROOM-WITH-COLUMN | Внутренний obstacle + OD/clearance | Нулевая запрещённая envelope intersection |
| ROOM-WITH-FORBIDDEN-ZONE | Нагрев запрещён только в typed polygon | BODY отсутствует внутри; exclusion не считается обязательным покрытием |
| MULTI-CIRCUIT | Два–три контура, полные длины включая service | Общая collision check, покрытие без double count, unique ports |
| DOOR-TRANSIT | Подтверждённый doorway и парная подводка | Коридор физически вмещает трубы/радиусы; BODY/TRANSIT раздельно |
| MANIFOLD-ROUTING | Exact connector frames, несколько пар | Port order, tangent/radius, no crossing; полная connection continuity |
| IMPOSSIBLE-GEOMETRY | Полоса слишком узкая под R/OD; blocked terminal | Никакого CAD-ready output; reason/witness |
| UNKNOWN-INPUT | Неизвестный finish-face/порт/проём | MissingVerifiedInput, не ProvenInfeasible |
| THIN-OBSTACLE-20 | Минимальный найденный counterexample | Отказ независимо от шага sampling |
| FALSE-EVIDENCE | Spacing metadata не соответствует реальному пути | Reject; checker строит собственное evidence |
| ARC-ONLY-COLLISION | Острые control segments безопасны, fillet нарушает стену | Reject по final physical arc |
| ADJACENT-OVERLAP | Разворот назад по тому же отрезку | Reject несмотря на adjacency |
| EXACT-THRESHOLD | Distance c−epsilon/c/c+epsilon | Conservative result, refinement/Indeterminate при недостаточной точности |

Значения RECT-01 — предлагаемый synthetic fixture, не принятый проект дома. До записи Valid golden сначала независимо проверить его геометрию. Не фиксировать статус PASS вручную из ожидаемого дизайна.

## Property tests

Генератор входов варьирует ширину/высоту, aspect ratio, pitch, R, wall clearance, число rings, расположение gateway. Особенно важны значения непосредственно до/после границы template applicability. Property: любой **возвращённый Valid** обязан проходить independent validator; допустимый отказ не должен превращаться в исключение/битый output.

Metamorphic свойства: translation и rotations/reflections сохраняют физические инварианты; перестановка starting vertex polygon не меняет канонический результат при одинаковых constraints; повторный запуск даёт тот же digest. Масштабирование применять только вместе со всеми размерными параметрами: фиксированный R80 нельзя оставить неизменным и ожидать инвариантного результата.

Не использовать `solver(input).valid == true` для всех случайных комнат. Полнота решения и корректность возвращённого решения — разные свойства. Проверять conservation площади после decomposition: union(cells)+явные reservations совпадает с исходным area в пределах численного бюджета, interiors cells не перекрываются. Отдельно проверять serviceability gateway.

Негативные мутации принятого candidate: переставить primitive, укоротить tangent, сдвинуть endpoint, вставить duplicate edge, подменить BODY роль, изменить source hash, добавить obstacle между samples. Каждая должна активировать конкретный rule ID. Shrinking сохраняет геометрический смысл и создаёт минимальный JSON reproduction.

## Реальный C05/C06: два набора истины

### Историческая геометрия D178

Источник: `homeaura-native-editor-generate/build_floor1_boiler_pair_178.py`, функции `c05_spec` и `c06_spec`; тест `homeaura-native-editor-tests/BoilerPair178Validation.cs`.

| Параметр | C05 | C06 |
|---|---|---|
| ID | F1-D171-C05 | F1-D171-C06 |
| Поле | x16400..18200, y9200..11600 | x18400..20600, y9200..11600 |
| Начало полевого BODY | (16400,9200,108) | (20600,11600,108) |
| Конец полевого BODY | (18200,11600,108) | (18400,9200,108) |
| Число Point3 всей трассы | 40 | 36 |
| BODY ranges по vertex endpoints | (1,3),(6,8),(11,36) | (1,3),(6,31) |
| Порты | 8/9 | 10/11 |
| Закреплённая rounded length | 46533.441827207615 mm | 45433.79285194222 mm |
| Закреплённая BODY length | 39307.25635973339 mm | 37341.592653589796 mm |

Массивы извлечены без исполнения build script в `evidence/C05_C06_D178_source_fixture.json`. Параметры полей совпадают с историческим описанием задания, но исходные full paths включают perimeter L-ranges и TRANSIT; первые/последние full-path точки не совпадают с BODY supply/return. Grammar этого артефакта — serpentine, не новая bifilar spiral. Golden legacy обязан воспроизводить старый результат и ограничения его claims, а не выдавать новую инженерную сертификацию.

Дополнительно выполнено сравнение с `HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185/HomeAura_TwoFloor_C12BoundedTerminal_D185.homeaura.json`: массивы C05 и C06 в D185 совпадают с D178, по 40 и 36 точек соответственно. Range semantics native analyzer: start включён, end исключён для индексов segments; соответствующие vertex endpoints включены оба. Это не то же самое, что inclusive segment range в отдельных внешних prompt contracts.

### Поздний contract / unresolved input

`reports/tmp/HomeAura_C05_C06_COMPACT_NORMATIVE_V2_packet.txt`:

* R04 source outline: `(16200,8500),(21300,8500),(21300,11800),(16200,11800)`.
* Inferred clear rectangle: x16300..21100, y8700..11700, 14.4 м²; declared area15.9 и prior artifact16.83 не согласованы. Inference не становится authoritative finish-face polygon.
* K1 XY=(16400,9300); derived port XY: p8=(16275,9187.5), p9=(16275,9412.5), p10=(16325,9187.5), p11=(16325,9412.5). World Z, connection direction/frame и tails отсутствуют.
* Window projections и verified passage gates в указанном packet отсутствуют. C07 и другие соседние трассы заморожены и должны участвовать в collision context.

Нужны fixtures `C05C06-LEGACY-D178`, `C05C06-BODY-SYNTHETIC-CONSTRAINTS` и `C05C06-FULL-MISSING-INPUT`. Для последнего ожидаемый результат — MissingVerifiedInput. Нельзя требовать успешного решения реального проекта, подставив удобные значения из synthetic rectangle.

## Формат replay и CI

Fixture хранит input JSON, policy versions, source provenance/hash, expected status, обязательные rule IDs, approved metric intervals; для доказанного deterministic template — canonical geometry digest. CI сохраняет при падении input, final primitives, report и маленький SVG. JSON + seed воспроизводит дефект без открытия AutoCAD.

Первый test project использовать с обычным test SDK и выбранным runner, обеспечить nonzero discovery и `dotnet test` на чистом CI. Core не должен ссылаться на Autodesk, Windows Forms, System.Drawing UI или browser runtime. Native исторические harness сохраняются отдельной Windows regression lane до переноса.

AutoCAD integration запускать при изменениях adapter либо по release gate: round-trip line/arc, transform/units, stale artifact rejection, идемпотентность по stable IDs, rollback, сохранность чужих entities. Использовать копию эталонного DWG и assertion по извлечённым entities, а не визуальный просмотр после каждого commit.

## Exit criteria первого solver

Каждый Valid result имеет одну цепь; отсутствие self/inter-circuit intersections/overlaps; ось и OD-envelope в разрешённой зоне; wall/obstacle clearance; правильные полезные spans pitch200 и edge100; Rmin и tangent feasibility; required supply/return position+direction; аналитическую длину; стабильный digest. Все canonical negative mutations отклоняются. Unknown, unsupported, budget exhaustion и proven infeasible не смешаны.

Переход к L/T запрещён до выполнения этих критериев для поддерживаемого rectangle family. Screenshot или 57 старых PASS не заменяют этот gate.
