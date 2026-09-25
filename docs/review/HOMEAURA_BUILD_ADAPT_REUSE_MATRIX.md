# HomeAura: Build / Adapt / Reuse matrix

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

## Решение для HomeAura 1.0

Не покупать и не строить универсальный geometry/coverage framework до доказанного rectangle solver. Библиотеки должны заменить commodities; небольшая собственная реализация остаётся на стыке инженерных правил, топологии и физических ограничений. Ни одна строка ниже не является командой удалить текущий код: замена выполняется по shadow tests и exit criteria.

**LIBRARY** — готовая зависимость; **ADAPT** — приспособить существующий подход/компонент; **BUILD** — собственная предметная логика; **EXTERNAL ENGINE** — отдельный CAD/BIM/runtime; **DEFER** — отложить. Legal usage modes и источники licenses подробно приведены в `HOMEAURA_GRAIL_RESEARCH.md`; «internal» означает текущий HomeAura code, а не проверенную лицензионную чистоту всей истории.

| Component | Current implementation / evidence | Candidate | License | Decision | Expected benefit | Migration difficulty | Risk |
|---|---|---|---|---|---|---|---|
| Room detection | RoomDiscoveryCommands выбирает marker/outline; RoomBoundaryCommands извлекает entities | Сохранить AutoCAD/MagiCAD extraction; semantic resolver с provenance | Autodesk proprietary; internal | ADAPT | Не переписывать native object access | Medium | DWG marker не равен authoritative room boundary |
| Polygon normalization | RoomGeometryMath, IFC importer, Python canonical helpers | Общий PrecisionPolicy + Clipper/NTS wrappers | BSL-1.0 / BSD-3 + notices | LIBRARY + ADAPT | Одни units/rings/error budgets | Medium | Молчаливый snapping меняет topology |
| Offsets | Ограниченные rectangle/lane shifts; Shapely в scripts | Clipper2 | BSL-1.0 | LIBRARY | Robust general polygons/holes | Low–Medium | Исчезающие узкие зоны; arcs linearized |
| Boolean geometry | Interval subtract, bespoke tests, Shapely union | Clipper2 Difference/Union | BSL-1.0 | LIBRARY | Heated area и obstacles без собственного boolean engine | Medium | FillRule/orientation/precision |
| Spatial index | Повторные pairwise loops в checkers | NTS STRtree/broad phase | BSD-3 + notices | LIBRARY | Ускорение global pair checks | Low | Broad phase не заменяет narrow phase |
| Zone decomposition | floor_heating_coverage, room-specific splits | Orthogonal sweep + typed portals; Fields2Cover ideas позже | Internal; BSD-3 для F2C | ADAPT | Компактные supported cells | Medium–High | Геометрически правильная cell может быть физически непроходима |
| Spiral generation | Python four-ring pattern; VIS templates | UFH Designer pinned benchmark, затем малый template при необходимости | Apache-2.0 кандидат; internal fallback | BUILD ограниченного rectangle; UFH остаётся кандидатом | Доказуемая малая область параметров | Medium | Center/gateway infeasibility |
| Meander generation | Lane engine; D178 arrays | Небольшой deterministic cell meander | Internal | ADAPT | Быстрое заполнение подходящих cells | Low–Medium | U-turn radius; return corridor |
| Bifilar generation | Fixed ring ordering / historical manual morphology | UFH Designer + проверка even-in/odd-out и center | Apache-2.0 кандидат; internal fallback | BUILD ограниченного rectangle, R3 | Надёжная counterflow topology | High | Нельзя исправить connector только offset library |
| Path stitching | Ручные arrays, orthogonal_route, imports D-scripts | Paired portal catalogue + offset linking research | Internal; paper idea, license code не установлена | BUILD + ADAPT | Явная проверка seam, radius, order | High | Local PASS не означает global PASS |
| Variable spacing | Hard-coded 100/200 bands, native exterior checks | Wall-indexed axis schedule + corner/transition templates | Internal | BUILD | Formal100/200 без скрытого300 | High | R80 несовместим с direct U100 |
| Obstacle avoidance | Sampled allowed_segment; Shapely scripts | Clipper inflated obstacles + NTS/analytic checks | BSL/BSD; Python deps отдельно | LIBRARY + ADAPT | Устранение пропуска узких obstacles | Medium | Physical envelope/holes semantics |
| Manifold routing | _orthogonal_route; per-house Point3 scripts; connection tolerance | Direction-aware graph + ordered pair corridor + physical refinement | Internal; OR-Tools Apache при необходимости | BUILD + ADAPT | Отделение service от BODY | High | Missing doors/connector frame, congestion |
| Circuit splitting | Coverage plan до трёх zones; scripts | Length-reserved spatial partitions + feasible candidates | Internal | ADAPT | Предсказуемый loop count | Medium–High | Area/p недооценивает connectors |
| Circuit balancing | Geometric length windows/spread в tests | OR-Tools candidate assignment, отдельная hydraulics layer | Apache-2.0 | DEFER → LIBRARY | Снижение combinatorial перебора | Medium | Equal length не равно hydraulic balance |
| Validation | Python validator; native CircuitAnalyzer; SVG certificate | Independent NTS + analytic physical rules; extract native checks | BSD-3; internal | LIBRARY + REFACTOR | Один contract, независимая проверка | High | Shared preprocessing и arc approximation |
| Optimization | Ручные варианты, эвристики, compare metrics | Feasible-only ranking; OR-Tools discrete layer | Internal/Apache-2.0 | ADAPT, затем LIBRARY | Не оптимизировать недопустимый дизайн | Medium | Любая мутация требует revalidate |
| AutoCAD import | plugin .NET4.8 entities→DTO | Сохранить official API adapter | Proprietary API | EXTERNAL ENGINE + ADAPT | Максимальная fidelity в текущем host | Low–Medium | Proxy/custom object coverage |
| AutoCAD export | FloorHeatingPayload + transactional renderer | ValidatedDesign + exact arcs/bulges, post-export replay | Proprietary API; internal | ADAPT | Не выпускать непроверенную геометрию | Medium | Старый JSON status не physical certificate |
| DWG/DXF offline | Основная ветка через AutoCAD; полный offline engine не подтверждён | ACadSharp для ограниченного subset | MIT | LIBRARY, ограниченный scope | Offline fixtures/import helpers | Medium | Нет подтверждённого full MEP round-trip |
| IFC | ifc_space_importer уже использует IfcOpenShell seam | Сохранить, выделить neutral contracts | LGPL-3.0-or-later core | EXTERNAL ENGINE / ADAPT | BIM без нового IFC parser | Medium | Units/placements/shape support/license package |
| Revit integration | Рабочий Revit csproj в этой копии не найден | Отдельный adapter Room/Space/MEP connector→contracts | Proprietary API | DEFER | Не блокировать BIM развитием current model | Medium–High | Версии runtime, exact connector semantics |
| AI orchestration | External coordinate candidates; API packages; deterministic Python core | Intent/tools/explanation only | Internal; provider terms | REFACTOR | Меньше дорогих координатных попыток | Medium | AI может неверно задавать параметры: schema/rules gate |
| Thermal/hydraulic design | Sizing явно ограничен declared assumptions; полного hydraulics нет | Verified product/rule data и отдельный solver | По выбранному компоненту | DEFER beyond geometry MVP | Честная степень engineering readiness | High | Нельзя назвать geometry MVP full installation design |
| Web/native UI | React web preview + WinForms editor | Использовать общий validated DTO | Текущие dependencies отдельно | KEEP / DEFER expansion | Не плодить ещё один geometry engine | Low–Medium | Rendering может скрывать physical defects |

## Почему не взять один внешний solver

| Кандидат | Снимает | Не подтверждено | Вывод |
|---|---|---|---|
| Clipper2 | Offset/booleans | Coverage topology/endpoints/R80 | Нужная primitive library |
| NTS | Topology predicates/distance/index | UFH semantics, exact curves, hydraulics | Независимый checker foundation |
| HeatGrid | Ограниченная rectangular filleted pattern idea | Source access/license, arbitrary terminals/obstacles | Reference, не dependency |
| Opti-Pipe | Graph/DFS routing prototype | Physical bend radius, deterministic budget, full rule set | Experimental reference |
| Fields2Cover | Coverage decomposition/route architecture | Single non-overlapping manufacturable pipe | Selective adaptation позже |
| Cura/Prusa | Mature polygon/path pipeline | One continuous fixed-OD loop + compatible closed-source license | Reference only |
| MagiCAD/HeatAlgo | Commercial workflow/behavior | Open reusable engine/API rights и HomeAura fixtures | Benchmark; buy only after specific evaluation |

## Условия коммерческого использования

Для permissive core libraries допустимы коммерческое применение и модификация с сохранением необходимых notices; disclosure HomeAura обычно не требуется. Проверить конкретные package contents, native runtime libraries и per-file licenses до shipping. LGPL integration отдельно проверяет replacement/relinking/source obligations. GPL/AGPL reference не переносить в source HomeAura без решения о совместимой лицензии. Неизвестная лицензия — не permissive license.

## Ожидаемая экономия

HIGH confidence: самописный polygon clipping/offset framework HomeAura не нужен. HIGH confidence: дублирующие distance/intersection implementations создают лишний риск. MEDIUM confidence: значительную часть D-script active workflow можно заменить parameterized templates + fixture replay. LOW confidence: точный net LOC deletion и календарное ускорение — пока нет prototype/adapter measurements.

Основная сложность после reuse: доказанные center/gateway patterns, variable spacing у нескольких стен, joint multi-circuit routing и достоверность физических исходников. Именно эти задачи нужно бюджетировать, вместо попытки оценить успех количеством удалённых строк.
