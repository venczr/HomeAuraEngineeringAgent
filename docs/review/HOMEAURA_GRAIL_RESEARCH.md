# HomeAura Grail Search: алгоритмы и внешние компоненты

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

## Результат поиска

Наиболее короткий реалистичный путь — **Clipper2 для областей + NTS для независимой 2D проверки + небольшой собственный каталог UFH patterns/connectors + отдельный routing planner**. OR-Tools полезен позже для дискретного выбора контуров и портов. IfcOpenShell уже имеет seam в проекте.

Не найден и не проверен open-source solver, который можно подключить и получить весь контракт Boundary/Holes/Obstacles/Start/End/Spacing/Rmin → continuous manufacturable bifilar path с perimeter100/200, несколькими контурами и физическими коллекторными подключениями. Это результат конкретного поиска, а не доказательство отсутствия такого проекта в мире. Процент «70–90%» нельзя честно присвоить без canonical benchmark.

Источники проверены 9 сентября 2026. Для mutable GitHub branches следует закрепить конкретные commit/package при начале POC. Локальные прочитанные внешние файлы использованы только для анализа, в HomeAura production code не включены. Все выводы об использовании — предварительная техническая license triage; распространяемый пакет требует SBOM конкретных версий и зависимостей.

## Computational geometry

### Clipper2 — USE AS DEPENDENCY

FACT: библиотека предоставляет polygon booleans и offsets, C#/C++ реализации; основной license — Boost Software License 1.0. В просмотренном `Clipper.Offset.cs` есть параметры joins/arc tolerance/miter limit, а результат offset проходит union cleanup. Это намного шире текущих ручных interval/rectangle helpers. [Исходник](https://github.com/AngusJohnson/Clipper2/blob/main/CSharp/Clipper2Lib/Clipper.Offset.cs), [license](https://github.com/AngusJohnson/Clipper2/blob/main/LICENSE).

RECOMMENDATION: заменить собственные операции построения heated area и subtraction; сохранять hole hierarchy и проверять topology после каждого offset. Nested offsets могут распасться на несколько областей. **Clipper2 не строит сам по себе бифилярную трассу, не обеспечивает endpoints и Rmin трубы.** Закрепить проверенную версию и отдельный regression corpus. В README upstream на момент просмотра имеется предупреждение о проблемах triangulation; не использовать её как основание MVP decomposition. [README](https://github.com/AngusJohnson/Clipper2/blob/main/README.md), [offset guidance](https://www.angusj.com/clipper2/Docs/Units/Clipper.Offset/Classes/ClipperOffset/_Body.htm).

### NetTopologySuite — USE AS DEPENDENCY

FACT: основной license — BSD-3-Clause, с third-party notices в license document; это не прежняя LGPL-лицензия исторических NTS packages. Проверка актуального файла важнее устаревшей карточки SourceForge. [License](https://github.com/NetTopologySuite/NetTopologySuite/blob/main/License.md).

RECOMMENDATION: polygon validity, line simplicity, containment, distance, spatial indexing. Не использовать NTS IsValid линии как единственную проверку self-crossing. Отдельно контролировать дуги и OD-envelope. Независимость от Clipper полезна, но shared normalization bug может испортить обоих: checker должен видеть исходные constraints и budget преобразований.

### Shapely/GEOS — уже используется в проекте

FACT локального кода: D178 generator импортирует Shapely LineString/Point/box/unary_union. Нельзя описывать проект так, будто зрелых geometry libraries в нём ещё нет. Кандидат для временного Python reference checker; не объявлять независимость от NTS полной, поскольку GEOS и NTS происходят из семейства JTS. Main production core предпочтительно не размножать на Python и C# без необходимости. Shapely имеет BSD-3-Clause; license и native dependencies конкретной Shapely/GEOS поставки ещё нужно зафиксировать. [Shapely license](https://github.com/shapely/shapely/blob/main/LICENSE.txt).

## AutoLISP-археология

### Lee Mac HeatGridV1-0.lsp — REFERENCE ONLY, source access ограничен

Найдены оригинальная дискуссия CADTutor и повторное размещение на Autodesk forums. Автор описывает максимальную filleted spiral внутри прямоугольной closed LWPolyline, работу в разных ориентациях и связь старта с первой вершиной; центральные полуокружности ориентированы вдоль длинной стороны. Это важный ограниченный rectangular template, не произвольный UFH solver с фиксированными обоими ends. [Lee Mac, CADTutor, январь 2013](https://www.cadtutor.net/forum/topic/43738-a-challenge-how-to-draw-this-floor-heating/), [Autodesk thread, 2023](https://forums.autodesk.com/t5/visual-lisp-autolisp-and-general/auto-heating-floor-pipes-lisp/td-p/12031415).

Сам файл вложения CADTutor вернул HTTP403. Поэтому **не установлено по исходнику**, использует ли именно HeatGrid последовательный offset, какова точная формула центра, углов и connection-level ordering. Эти вопросы остаются открытыми; не приписывать Lee Mac код соседнего автора. Права на перенос кода не установлены. До получения доступного source/license — изучать изложенную геометрию, не копировать реализацию.

### heat-spiral M. Ribar — PORT IDEA, не готовая dependency

В той же CADTutor дискуссии доступен inline AutoLISP: создание LINE/ARC, explicit centers/radii, циклическое изменение радиусов и PEDIT join; присутствуют варианты с offset прямоугольника и центральными соединениями. Это позволяет изучить аналитическое построение уровней и дуг. Выбор прямоугольника, CAD commands, osmode и соединение entities встроены в алгоритм. Нет показанного независимого HomeAura-level validator или общего obstacle/terminal/R80 контракта. Публичный форумный код не сопровождается установленной permissive лицензией; переносить идею через самостоятельную спецификацию, не source.

### Snake Fill — REFERENCE ONLY

Опубликован инструмент M. Ribar для заполнения между двумя curves, а также исходная форумная дискуссия `snakefill-2curveboundaries`. Полезен для bounded meander/residual fill, не эквивалентен двухзаходной улитке. Из страницы загрузки нельзя вывести точную реализацию и условия redistribution. [Карточка CAD Forum](https://www.cadforum.cz/en/download.asp?fileID=3573), [обсуждение автора](https://www.cadtutor.net/forum/topic/48627-filling-up-one-area-with-a-quotorientedquot-polyline/).

## Академический UFH

Shi, Qiu, Yang, **A hierarchical layout approach for underfloor heating systems in single-family residential buildings**, Energy and Buildings 268, 112208, 2022. Публикация разделяет routing и coverage, использует routing graph/shortest paths с упорядочиванием трасс и recursive depth-first упрощение покрытия до прямоугольных layouts. Это прямое подтверждение полезности decomposition + small solvers. Однако приведённые примеры не являются гарантией произвольных endpoints, variable pitch и R80 HomeAura. Доступны abstract/introduction/section snippets; полный алгоритм и supplementary source в этом аудите не получены. [DOI / publisher](https://www.sciencedirect.com/science/article/pii/S0378778822003796).

RECOMMENDATION: принять разделение задачи; самостоятельно определить portal contracts и физическую проверку. Не обещать точный порт SPR/DFL без полного текста/pseudocode и проверки прав. Исследовательский результат на нескольких домах не означает production completeness.

Дополнительный lead: **From Meander Designs to a Routing**, опубликованный PDF Wolfram/Complex Systems. Нужен отдельный разбор graph/topology условий; полного source solver не подтверждено. [PDF](https://wpmedia.wolfram.com/uploads/sites/13/2019/01/20-4-6.pdf).

## CAM и непрерывная печать

### Continuous toolpath from offset contours — высокий интерес для stitching

Nguyen et al., 2023: offset contours переупорядочиваются по вложенности, выбираются пары breakpoints и их проекции на соседний contour, затем формируются связанные subpaths. Статья подробно описывает pipeline; для offsets использует Clipper. Алгоритм ориентирован на robotic cold spray, поэтому непрерывность не переносит автоматически UFH radius/spacing/connection guarantees. Особенно полезно отделение breakpoint search от offset generation. [Полный HTML, Springer](https://link.springer.com/article/10.1007/s40430-023-04544-9).

RECOMMENDATION: PORT IDEA для каталога парных portals. Самый близкий reuse — топология сшивки, а не CAD code. После каждого merge требуются global collision и coverage checks. Лицензия статьи и лицензия потенциального software supplementary — разные объекты; готовой dependency из статьи не получено.

Bi et al., **Continuous contour-zigzag hybrid toolpath for large format additive manufacturing**, 2022: сочетание contour и residual zigzag предлагает полезную стратегию для остатков. Полный текст/код не проверены, использовать как исследовательский lead, а не основу production. [Publisher](https://www.sciencedirect.com/science/article/abs/pii/S2214860422002226).

Spiral pocketing CAM решает удаление материала: возврат по уже обработанной области и tool lifts часто допустимы. Для трубы они могут быть запрещены. Поэтому переносим offsets, medial/sweep decomposition и linking constraints, но не принимаем CNC continuity за pipe manufacturability. Старое обсуждение NativeCAM показывает отдельные pocketing subroutines, не UFH guarantees. [NativeCAM discussion](https://github.com/FernV/NativeCAM/issues/4).

### PrusaSlicer и CuraEngine — REFERENCE ONLY

Прочитан Prusa `FillConcentric.cpp`: nested `offset2_ex`, порядок outside-in, разрезание loops по nearest point, clipping концов. Выход — набор polylines; код не обещает одну supply-return трубу. Solid spacing adjustment и variable extrusion width нельзя автоматически переносить в фиксированный p200/OD16. [Точный файл](https://github.com/prusa3d/PrusaSlicer/blob/master/src/libslic3r/src/libslic3r/Fill/FillConcentric.cpp), [проект](https://github.com/prusa3d/PrusaSlicer).

У Cura рассмотрены официальная архитектура генерации paths и `InfillOrderOptimizer.cpp`: ordering отделён от geometry generation. Это полезная архитектурная идея, но travel moves и отдельные extrusion paths отличаются от бесстыковой трубы. Core engines имеют AGPL-профиль; не включать source в закрытый HomeAura без отдельного решения о лицензировании. [Cura paths](https://github.com/Ultimaker/CuraEngine/wiki/Generating-Paths), [исходник ordering](https://github.com/Ultimaker/CuraEngine/blob/main/src/InfillOrderOptimizer.cpp), [CuraEngine](https://github.com/Ultimaker/CuraEngine).

## Robotics / coverage planning

Choset/Pignon boustrophedon decomposition разбивает свободное пространство на cells, удобные для back-and-forth покрытия. Это подходящая основа ZoneDecomposer, но робот может повторно проходить место/менять направление; постоянная труба не может. Hamiltonian coverage и spanning-tree traversal дают топологические идеи, однако grid graph без физических footprints недостаточен. [CMU original publication](https://publications.ri.cmu.edu/coverage-path-planning-the-boustrophedon-decomposition).

Fields2Cover — BSD-3-Clause, модульная C++ библиотека agricultural coverage. Прочитан `boustrophedon_decomp.cpp`: split lines строятся от ring vertices в заданном направлении; применяется собственная geometry wrapper. Полезны decomposition/swath/route seams. Перенос всего runtime ради rectangle MVP преждевременен; dependency tree и GEOS/GDAL-like geometry stack требуют отдельной поставочной проверки. Curvature-aware vehicle paths не доказывают self-avoiding UFH circuit. [Repository](https://github.com/Fields2Cover/Fields2Cover), [source](https://github.com/Fields2Cover/Fields2Cover/blob/main/src/fields2cover/decomposition/boustrophedon_decomp.cpp), [license](https://github.com/Fields2Cover/Fields2Cover/blob/main/LICENSE).

## Pipe routing / Opti-Pipe

**Opti-Pipe (felixscode)** — MIT, реальный Python prototype. Прочитан `src/opti_pipe/router.py`, license называется `LICENZE`. Naive routing вызывает NetworkX shortest_path; heuristic routing расширяет пути DFS по неиспользованному графу. `DFSSolver.solve` выбирает longest найденный path за time budget. Это не гарантирует одинаковый результат на разных машинах. Более того, `next(generator)` находится внутри time loop и сам может занять долгое время: timeout не является жёсткой верхней границей вычисления. В просмотренном router нет физического bend-radius checker; документация оставляет non-rectangular и robustness tests в TODO. [Source](https://github.com/felixscode/opti-pipe/blob/main/src/opti_pipe/router.py), [MIT license](https://github.com/felixscode/opti-pipe/blob/main/LICENZE).

Вердикт: PORT IDEA / EXPERIMENTAL. Ни тепловая convolution картинка, ни длинный simple grid path не доказывают engineering correctness. Не устанавливался и не запускался полный пакет с GPU dependencies: для решения об отказе от прямой замены достаточно выявленного несовпадения контрактов. [Author description](https://felixschelling.com/posts/optipipe/) доступен в поисковом индексе, прямой open вернул404; выводы о коде основаны на GitHub.

`cpp_SpiralFloorHeating` — дополнительный C++ lead, ориентирован на оценку длины прямоугольной спирали, а не полноценное routing API. Не включён в dependency shortlist: исходник и license не прошли здесь детального аудита. [Repository](https://github.com/marcin-filipiak/cpp_SpiralFloorHeating).

## PCB/VLSI и OR-Tools

Freerouting — GPL-3.0 PCB autorouter; полезен как behavioral/reference источник для escape routing, detailed routing и конфликтов. Слои платы и vias не соответствуют автоматически разрешённым pipe elevations и S-bends. Не рекомендован как библиотека закрытого HomeAura. [Repository](https://github.com/freerouting/freerouting), [architecture](https://github.com/freerouting/freerouting/blob/master/docs/architecture.md).

RECOMMENDATION: maze/Lee search или A* на corridor graph, state=(position,direction,layer,pipe-order), с physical refinement. Rip-up/reroute допускается только с bounded search и повторной глобальной проверкой. Не переносить PCB geometry/clearance model буквально.

OR-Tools — Apache-2.0, C#/C++/Python optimization toolkit. Кандидат для assignment, circuit count, capacity/length constraints и conflict-aware выбора уже сгенерированных вариантов. Exact route length поступает от geometry engine; CP-SAT не должен получать миллионы переменных для каждой координаты трубы на первом MVP. [Official repository/license](https://github.com/google/or-tools).

## Коммерческие benchmarks

HeatAlgo, release17 July2026: заявляет spiral/meander/bifilar meander, connection-aware patterns, real outline, отказ от невозможной геометрии и splitting. В частности, spiral в L-комнате рекомендует разделение; входная полоса может быть оставлена свободной согласно их coverage policy. Это **vendor claims**, не независимый benchmark HomeAura; их exemptions нельзя автоматически принять при требовании полного покрытия HomeAura. [Release](https://heatalgo.com/en/blog/update-july-2026-3/).

MagiCAD описывает routing suggestions с shape/obstacles/cold walls и задаваемыми входом/выходом. Но release notes MagiCAD for BricsCAD 2025 отдельно предупреждают, что spiral pattern не учитывает obstacles. Нельзя объединять разные host/version capabilities и выдавать за гарантии MagiCAD2024. Для сравнения нужен запуск конкретной установленной версии на одинаковом fixture. [Routing feature](https://www.magicad.com/tools/machine-learning-algorithm-for-automatic-routing-of-underfloor-heating-circuits-2/), [version-specific release notes](https://portal.magicad.com/Downloader.ashx?id=12181&type=product).

## CAD / BIM

AutoCAD .NET API остаётся основным reader/writer для реального MEP DWG. ADN/APS samples полезны для database transactions, commands и hosting, но не являются готовым UFH ядром. Каждому заимствуемому sample нужна своя license. Core Console снижает ручной труд в integration checks; поддержка конкретного плагина/MEP objects должна проверяться. [Core Console](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/How-to-use-the-AutoCAD-Core-Console.html), [APS plugin adaptation](https://aps.autodesk.com/blog/how-convert-your-plugin-work-design-automation-autocad).

ACadSharp — MIT C# DWG/DXF reader/writer. Рассматривать для ограниченного offline обмена и fixtures, но не принимать полную совместимость MagiCAD custom/proxy entities без round-trip corpus. [Project](https://github.com/DomCR/ACadSharp), [license](https://github.com/DomCR/ACadSharp/blob/master/LICENSE).

APS Automation предоставляет cloud CAD engines; это вариант будущего deployment, не нужная зависимость rectangle MVP. Pricing, host engine availability, custom add-in rights и данные проверяются перед покупкой/развёртыванием. [Official service](https://aps.autodesk.com/automation-apis).

IfcOpenShell предоставляет IFC parsing/geometry; текущая экосистема содержит разные licenses: core LGPL-3.0-or-later, Bonsai GPL-3.0-or-later. Выбирать конкретный component, не распространять всю экосистему как «одна LGPL библиотека». Existing Python importer следует сохранить и улучшить provenance/units. [Official repository and component licenses](https://github.com/IfcOpenShell/IfcOpenShell).

## Лицензионная матрица

«Коммерчески разрешено» не означает «можно встроить без условий». Static/dynamic ниже — техническая оценка для закрытой поставки, не окончательный юридический вывод. Все перечисленные reuse требуют сохранения notices и анализа фактически включённых third-party components.

| Компонент | License | Commercial / modification | Disclosure | Static / dynamic | Решение / риск |
|---|---|---|---|---|---|
| Clipper2 core | BSL-1.0 | Да / да | Не требуется раскрытие HomeAura | Оба возможны с условиями license/notices | USE AS DEPENDENCY; низкий, проверить per-file notices |
| NTS current | BSD-3 + third-party notices | Да / да | Не требуется раскрытие HomeAura для permissive поставки | Оба возможны | USE AS DEPENDENCY; низкий после SBOM |
| OR-Tools | Apache-2.0 | Да / да | Не требуется раскрытие HomeAura; notices/changes/patent terms | Оба возможны, native deps проверить | USE AS DEPENDENCY позже; низкий/средний |
| Fields2Cover | BSD-3 | Да / да | Core не требует раскрытия HomeAura | Оба по core license; deps отдельно | PORT IDEA/ADAPT; средний integration |
| Opti-Pipe | MIT | Да / да | Нет обязательного disclosure по MIT | Допустимы аналоги встраивания; Python deps отдельно | PORT IDEA; высокий algorithm risk |
| Shapely | BSD-3-Clause | Да / да по core license | Нет по Shapely core; GEOS package отдельно | Python binding/native linking требуют анализа поставки GEOS | Временный reference checker; package clearance не завершён |
| ACadSharp | MIT | Да / да | Нет | Оба возможны | LIMITED DEPENDENCY; MEP fidelity risk |
| IfcOpenShell core | LGPL-3.0-or-later | Да / да при выполнении условий | Изменения library и corresponding source obligations; не автоматически весь HomeAura | Dynamic проще; static требует условий relinking/installation info по применимости | EXTERNAL/ADAPTER; средний license integration |
| Bonsai | GPL-3.0-or-later | Да / да под GPL | Для распространяемого производного/combined work применим copyleft | Dynamic не снимает copyleft автоматически | REFERENCE ONLY для закрытого core |
| CuraEngine / PrusaSlicer | AGPL-3.0; пакет/версию проверить | Да / да под AGPL | Copyleft; network interaction условия для модифицированной версии | Ни static, ни dynamic не являются автоматическим исключением | REFERENCE ONLY; высокий для closed embedding |
| Freerouting | GPL-3.0 | Да / да под GPL | Corresponding source при применимых условиях distribution | Dynamic не освобождает автоматически | REFERENCE ONLY |
| HeatGrid / heat-spiral / Snake Fill | Права на включение не установлены | Не подтверждено для включения source | Не определено | Не разрешено предполагать | REFERENCE ONLY / PORT IDEA без копирования |
| Academic papers/pseudocode | Publication-specific | Идеи отдельно от copyright code | Не software dependency license | Неприменимо | PORT IDEA; проверять supplementary отдельно |
| Autodesk/MagiCAD/HeatAlgo | Proprietary | По коммерческому договору | По договору | Не произвольная linkable library | BENCHMARK / EXTERNAL ENGINE |

Вынос GPL/AGPL в subprocess сам по себе не является доказательством отсутствия copyleft obligations. Не требуется запрещать GPL research, но нельзя смешивать идею и дословный порт implementation. Полного license clearance/патентной свободы этот документ не устанавливает.

## Патенты, форумы и непройденные ветки

Найден CN114970062A: сеточная abstract main-axis схема с производными offset points. Полезен как указатель на topology → paired offsets, но публикация патента не даёт разрешение применять защищённые claims. Status/family/jurisdiction/FTO не проверены. [Patent publication](https://patents.google.com/patent/CN114970062A/en).

McNeel содержит конкретное обсуждение rectangular spiral для radiant floor; Dynamo floor-heating thread — главным образом работа с room elements, не подтверждённый полный solver. [McNeel](https://discourse.mcneel.com/t/rectangular-spiral/132131), [Dynamo](https://forum.dynamobim.com/t/floor-heating/3578).

Поиск включил GitHub, GitLab, SourceForge, CADTutor, Autodesk, CAD Forum, McNeel/Dynamo, publisher papers, университетские страницы и патенты. По GitLab/SourceForge не найден дополнительный проверенный UFH solver. AUGI, все theses и все supplementary repositories исчерпывающе не просмотрены. HeatGrid source blocked403; полный UFH HLA paper недоступен в прочитанном представлении. Эти gaps не заменяются выдуманным алгоритмом.

## Приоритет исследований

1. Закрепить Clipper2/NTS версии и измерить rectangle POC на общих fixtures.
2. Проверить ring/gateway/center catalogue для R80 и100/200; это основной production bottleneck.
3. Получить доступный HeatGrid source и полный HLA текст при необходимости уточнить алгоритм, но не блокировать ими независимый rectangle proof.
4. Изучить Springer breakpoint stitching и Fields2Cover cells на L/T после завершения rectangle gate.
5. Включить OR-Tools только при измеренном combinatorial bottleneck assignment/balancing.
