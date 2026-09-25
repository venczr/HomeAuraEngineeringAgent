# HomeAura: поэтапная миграция к проверяемому Floor Engine

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

## Рабочее правило

Не переписывать проект целиком. Новое ядро развивается рядом со старым под feature flag, старые API и исходные DWG сохраняются. Новая геометрия становится доступна exporter только после independent validation. Разработка начинается с одного ограниченного эксперимента; нижеследующие этапы не были выполнены в рамках аудита.

Оценки сложности относительные. Календарные сроки и процент экономии до запуска POC ненадёжны. Полный engineering product включает hydraulic/thermal/physical inputs, которых geometry MVP сам по себе не завершает.

## M0 — закрепить исходные данные и сравнимый baseline

**Goal:** воспроизводить именно рабочий snapshot, включая незакоммиченные исходники, без потери пользовательских изменений.

**Files/components affected:** audit evidence; selected source manifest; canonical fixtures; `build_floor1_boiler_pair_178.py`, D178/D185 contracts read-only.

**Expected result:** source hashes, подтверждённая актуальная копия, fixtures с provenance и явным разделением legacy/synthetic/unknown physical inputs. Сохранить текущие console/Python результаты.

**Tests:** hashes соответствуют файлам; replay D178; helper thin-obstacle reproducer; проверить read errors inventory.

**Rollback:** удалить только новые snapshot/fixture artifacts; исходники не тронуты.

**Exit criteria:** любой важный вывод аудита привязан к файлу/тесту; C05/C06 endpoints/roles не перепутаны. Не требовать заполнения неизвестных данных для synthetic BODY POC.

## M1a — checker и benchmark готового кандидата

**Goal:** сравнить закреплённый UFH Designer с заранее фиксированным контрактом до собственной реализации.

**Files/components:** изолированный Python/Shapely checker, ручной line/arc fixture, JSON/SVG и headless TypeScript runner; production assemblies не менять.

**Exit criteria:** checker принимает известную допустимую бифилярную конструкцию, отклоняет мутации и проверяет обязательные свойства; затем обоснованное ADAPT/BUILD. Недостаточность checker — отдельный незавершённый gate.

**Факт:** прогон выполнен; прямой выход не проходит контракт. Checker откалиброван только на геометрической змейке и шести мутациях. Общий результат CHECKER_INSUFFICIENT, M1a не закрыт. См. отдельный benchmark.

## M1b — один p200/R80 шаблон после решения M1a

**Goal:** адаптировать подтверждённый внешний алгоритм либо построить один малый rectangle template при обоснованном BUILD.

**Expected result:** deterministic JSON→line/arc JSON с exact endpoints/tangents и полным независимым checker. Без CAD/UI, perimeter100 и C05/C06. Не создавать заранее framework или множество assemblies.

**Tests:** известный Valid bifilar fixture; шесть изолированных отрицательных проверок, подложный spacing evidence, граничные размеры, преобразования, повторяемость. Неопределённость обязательного правила блокирует экспорт.

**Rollback:** отключить эксперимент; production остаётся прежним. Известные дефекты legacy не становятся допустимыми.

**Exit criteria:** все обязательные правила Pass; достаточная успешность внутри объявленной области. До этого M2 не начинать.

## M2 — perimeter100/200 и C05/C06

**Goal:** решить реальную сложность проекта формальными edge/gateway constraints.

**Files/components affected:** POC spacing policy, edge/corner/center templates; fixtures C05C06; новые checker rules.

**Expected result:** три edge axes100/200/300 с nominal field200, корректные R80 переходы; legacy D178 остаётся неизменным; неизвестные full-design inputs дают MissingVerifiedInput.

**Tests:** RECT-EDGE-100-200, two-wall corner, window-span, U100 rejection, reserved gateway coverage, legacy hash replay, new BODY-only geometry с explicit synthetic terminals.

**Rollback:** отключить новый pattern family. Не ослаблять validator ради прохождения кейса.

**Exit criteria:** нет шага300 на полезных field spans, нет artificial length balancing, полный negative corpus отклоняется. Для реального full C05/C06 GO отдельно нужны confirmed finish faces/openings/port frames; отсутствие этих данных не лечится solver.

## M3 — выделить reusable geometry и native physical checks

**Goal:** превратить POC в библиотеку и сохранить сильные стороны native analyzer.

**Files/components affected:** `homeaura-native-editor/ProjectModel.cs`, `CircuitAnalyzer.cs`, csproj tests/generate/editor; новые Core/Validation modules.

**Expected result:** immutable curve model и materialization вне Windows Forms; native editor вызывает библиотеку. Старые JSON через migration adapter, public commands сохраняются.

**Tests:** 57-case native harness как characterization suite, новые core tests, line/arc/Point3 equivalence, source-role ranges→primitive IDs conversion. Проверять deterministic diagnostics и error bounds.

**Rollback:** вернуть ссылку на прежний analyzer через flag; новые файлы остаются изолированными.

**Exit criteria:** core unit tests запускаются без UI/CAD; historical accepted и blocked states не повышены; fixed-point/double policy одна и версионирована. Native tests не исчезли при переносе.

## M4 — shadow integration Python/API

**Goal:** один authority для нового solver, без резкой смены API.

**Files/components affected:** `agent/floor_heating_engine.py`, `floor_heating_coverage.py`, `floor_heating_models.py`, preview/system graph adapters.

**Expected result:** старый endpoint может запускать V2 в shadow и сохранять comparison report; клиент пока получает прежний контракт. Решить measured trade-off in-process netstandard core vs отдельный JSON process. Не переносить весь Python backend в C#.

**Tests:** одинаковый input/provenance; schema backwards compatibility; failure mapping; cancellation; stale report/digest; no duplicate geometry authority. Сравнивать invariant outcomes, не требовать совпадения координат при исправлении старого дефекта.

**Rollback:** feature flag выключает V2; shadow reports не меняют authoritative project.

**Exit criteria:** расхождения объяснены; старый bug не превращён в новый expected golden; неподдерживаемые cases возвращают корректный отказ.

## M5 — gate AutoCAD export

**Goal:** production DWG получает только проверенную final geometry.

**Files/components affected:** `FloorHeatingPayload.cs`, `FloorHeatingCommands.cs`, `FloorHeatingRenderer.cs`; новый validated artifact contract.

**Expected result:** exact line/arc export, validation bound to input/result/config hash; idempotent ownership, транзакционный rollback; отделён diagnostic preview.

**Tests:** round-trip на копии DWG; units/UCS/bulge; stale/forged status rejection; mismatch hash; no-op/idempotency; сохранность чужих entities; failure halfway rollback. accoreconsole compatibility проверить именно с установленной версией.

**Rollback:** flag возвращает legacy preview command; новая production-write ветка отключается. Не откатывать пользовательские DWG заменой файлов.

**Exit criteria:** imported final curves повторно проходят checker; old `status=ok` без physical report не даёт V2 installation output.

## M6 — decomposition + manifold detailed routing

**Goal:** расширить поддерживаемые формы и число контуров.

**Files/components affected:** новые ZonePlanner/PathStitcher/ManifoldRouter; coverage adapter; shared building obstacles/ports.

**Expected result:** L/T/holes только через certified cells и portals; раннее corridor reservation; global conflict validation; realistic pipe length budgets.

**Tests:** L/T/column/forbidden-zone, door capacity, exact manifold frames, inter-circuit and physical S-bend cases; impossible neck and unreachable return; non-overlapping partition union.

**Rollback:** исключить новые pattern families из supported set; rectangle path остаётся.

**Exit criteria:** новые формы не ослабляют ни одного старого gate; после stitching и routing выполняется full validation. Partial layout не называется complete design.

## M7 — discrete optimization и сокращение legacy

**Goal:** уменьшить перебор и maintenance после доказанного baseline.

**Files/components affected:** OR-Tools assignment layer при измеренной потребности; VIS variants, duplicated Python geometry, historical generator imports.

**Expected result:** ranking feasible candidates, bounded search, policy-weighted choices; active product перестаёт импортировать D-scripts. Legacy fixtures и provenance архивируются отдельно.

**Tests:** feasibility preservation, deterministic solver settings, impossible capacities, no fabricated length; dependency scans and all affected entrypoint replay перед удалением.

**Rollback:** отключить optimizer; восстановить удалённую implementation из version control. Удаление отдельными маленькими changes, не вместе с solver rollout.

**Exit criteria:** доказано отсутствие active consumers каждого удаляемого файла; licenses/SBOM завершены; улучшение измеряется временем/дефектами/числом ручных действий, не только LOC.

## M8 — BIM и full engineering после geometry MVP

**Goal:** совместимый IFC/Revit workflow и инженерные расчёты без загрязнения geometry core.

**Files/components affected:** IFC importer/domain contracts; отдельный Revit adapter; thermal/hydraulic/product rule modules.

**Expected result:** stable room/space IDs, placements/units, verified connectors/openings, heat-demand constraints, реальные гидравлические проверки.

**Tests:** IFC fixture corpus и Revit host integration; cross-floor datum; end-to-end system claims; heat/pressure rule cases с источниками данных.

**Rollback:** adapters отключаются независимо от floor solver.

**Exit criteria:** geometry Valid отделён от thermal/hydraulic/install-ready; существующие помещения не получают выдуманные physical properties.

## Ответы на 20 критических вопросов

1. **Что оставить?** CAD adapters, atomic/strict contracts, domain/IFC seams, инженерные правила, native physical diagnostics и regression artifacts.
2. **Что удалить?** После replacement/replay — дублирующие primitives и legacy experiments из active execution; сейчас не удалять рабочие файлы.
3. **Что зря пишем сами?** Общие polygon predicates/offset/boolean/index engines и новые копии одной и той же математики для SVG/CAD/Python.
4. **Какие библиотеки заменят?** Clipper2 — области; NTS — checker/index; OR-Tools — discrete assignment; ACadSharp — ограниченный offline CAD; IfcOpenShell — IFC (уже используется).
5. **Сложнейшая оставшаяся задача?** Физически допустимая совместная topology100/200/R80/endpoints/service/multiple circuits при достоверных входных данных.
6. **Есть готовые70–90%?** Подтверждённого solver под весь контракт не найдено; процент без benchmark не обоснован.
7. **Кратчайшая комбинация?** Clipper2 + NTS + small rectangle/edge/gateway catalogue + отдельный ordered routing; optimizer позже.
8. **Нужен один FloorSolver?** Единый façade допустим; единый гигантский алгоритм — нет.
9. **Лучше decomposition + small solvers?** Да для контролируемого supported domain, при явных portals и global validation; decomposition сама не гарантирует routing.
10. **Как гарантировать rectangle bifilar?** Аналитические nested levels, alternating inward/outward order, проверенные center/gateway templates, явные applicability inequalities и независимый final checker.
11. **Как100/200?** Wall-indexed axis sequence100/200/300/500/700…, отдельные corner/transition contracts; не arbitrary tube nudging.
12. **Как доказать отсутствие пересечений?** Полная topology/pair проверка final lines/arcs, overlap/touch/OD clearances, conservative error bounds; не sparse samples.
13. **Как Rmin?** Physical arcs и tangent reserves до принятия candidate; global clearance после fillet. Direct U100/R80 отклоняется.
14. **Как подводка?** Резерв парных коридоров до BODY freeze; direction-aware routing, port order, exact physical refinement.
15. **Как несколько контуров?** Spatial partition с service length reserve → реальные feasible candidates → assignment и global checks.
16. **Optimization vs feasibility?** Hard feasibility у constraints/generator+validator; optimizer выбирает прошедшее, любые мутации проходят revalidation.
17. **Как unit-reproduce баг?** Canonical input JSON + policy/version + seed + physical primitives/witness, всё без DWG runtime.
18. **Как не открывать AutoCAD вручную?** Core `dotnet test` на каждое изменение; host integration только для adapter changes/release, на копиях DWG.
19. **Что мешает сейчас?** Windows Forms assembly dependency, linked console test harness, historical filesystem/subprocess imports, несколько geometry authorities и point-array artifacts вместо параметрических fixtures.
20. **Самый короткий MVP путь?** M0→M1a→M1b→M2; затем извлечение core и gated export. Никаких L/T/general optimization до rectangle gate. Полный C05/C06 требует отдельно устранить physical input blockers.
