# HomeAura — возможности субагентов и роли (проверка 2026-09-21)

## 1. Фактические возможности текущей сессии

Проверено вызовом инструментов напрямую (не по догадке).

- **Субагенты доступны.** Инструменты запуска присутствуют и отвечают:
  `collaboration__spawn_agent`, `collaboration__list_agents`,
  `collaboration__send_message`, `collaboration__followup_task`,
  `collaboration__wait_agent`, `collaboration__interrupt_agent`.
  `list_agents` в начале сессии вернул только корневого агента `/root`
  (статус `running`) — запущенных субагентов ещё не было.
- **Конкуренция:** 4 слота одновременных агентов (включая корневого).
  Значит, в параллель безопасно запускать до 3 субагентов.
- **Модели для субагентов** (из схемы `spawn_agent`, не экспериментально):
  - `deepseek-flash` (reasoning: low / high (по умолчанию) / max);
  - `deepseek-v4-pro` (reasoning: low / high / max).
  По умолчанию субагент наследует родительскую модель (`deepseek-v4-pro`).
  `fork_turns`: `none` / положительное целое / `all`.
- **Активная модель сессии:** `deepseek-v4-pro` (подтверждено системным
  контекстом и маршрутизацией TokenWave: `ANALYSIS=deepseek-v4-pro`).

### Поддерживаемые параметры (только из схемы инструментов)

`spawn_agent(task_name, message, fork_turns, model, reasoning_effort)`.
Никакие иные параметры (в т.ч. «experimental») не используются.

## 2. Наблюдаемая конфигурация (снимок)

- **MCP-серверы, доступные в этой сессии:**
  - `cce_homeaura` — Context Code Engine (статус индекса: operational;
    включено сжатие вывода `standard`, экономия ~99% токенов на запросах).
  - `cua_repl` — unified computer use (управление UI).
  - `node_repl` — постоянный Node REPL.
  - Нативные MCP-инструменты ресурсов:
    `list_mcp_resources`, `list_mcp_resource_templates`, `read_mcp_resource`.
- **RTK:** в этой сессии RTK не экспонирован отдельным MCP-инструментом.
  Маршрутизация моделей задаётся файлами:
  `tools/tokenwave_mcp/config.json` и `tools/autonomous_supervisor/policy.json`
  (роль `ANALYSIS` = `deepseek-v4-pro`, `REVIEW` = `claude-haiku-4-5` и т.д.).
- **Файловая песочница:** `workspace-write`; запись разрешена в
  `C:\AI\HomeAuraEngineeringAgent` и временные каталоги; `.git`, `.agents`,
  `.codex` доступны только на чтение.
- **Утверждённые префиксы команд:** присутствуют (git commit, ряд
  PowerShell/python-команд аудита и сборки); новые не добавлялись.
- **Секреты:** в сессии не записывались; конфигурация содержит только ссылки
  на переменные окружения (например `api_key_env: OPENAI_API_KEY`), самих
  ключей нет.

## 3. Роли субагентов (этап 1 — ТОЛЬКО ЧТЕНИЕ)

Все три роли на первом этапе работают строго на чтение: запрещены любые
изменения файлов, `apply_patch`, `git add/commit`, запись в проектные данные.
Единственный координатор изменений — корневой Codex.

### GEOMETRY_AGENT
- **Зона анализа:** геометрия отдельных помещений и улиток.
- **Вопрос:** что мешает построению самостоятельных улиток/разбиению
  помещений в Test_01: R80, расстояние между трубами, расположение
  терминалов, выходы через двери.
- **Ключевые модули:** `agent/ufh_layout_engine.py` (`classify_strategies`,
  `choose_strategy`, `build_bifilar_spiral`, `validate_bifilar_topology`,
  `build_meander`, `split_required`), `agent/ufh_spiral_kernel.py`,
  `agent/ufh_bend_geometry.py`, `agent/ufh_zone_layout.py`;
  данные: `dev/ufh_spiral_validation/spiral_validation.json`,
  `dev/ufh_real_plan/layout_strategy_summary.json`; тесты:
  `tests/test_ufh_layout_engine.py`, `tests/test_ufh_spiral_kernel.py`.

### BUILDING_ROUTING_AGENT
- **Зона анализа:** граф помещений и здание в целом.
- **Вопрос:** реальные и неподтверждённые проёмы, число подач/обраток каждого
  контура, распределение труб по коридорам, доступное транзитное пространство.
- **Ключевые модули:** `agent/ufh_building_routing.py` (`route_building_system`),
  `agent/ufh_global_planner.py`, `agent/ufh_room_planner.py`;
  данные: `dev/ufh_real_plan/building_connectivity.json`,
  `building_openings.json`, `manifold_connections.json`, `riser_schedule.json`,
  `transit_capacity.json`, `transit_validation.json`, `building_ufh_summary.json`.

### PHYSICAL_VALIDATOR
- **Зона анализа:** независимая проверка выходов двух планировщиков.
- **Вопрос:** нарушения непрерывности, длины 90 м, R80, зазоров, пересечения,
  дублирование сегментов, ошибочно присвоенные статусы `VALID`.
- **Ключевые модули:** `agent/ufh_physical_validation.py`,
  `agent/ufh_room_validation.py`, `agent/ufh_room_planner.py`,
  `agent/ufh_bend_geometry.py`;
  данные: `dev/ufh_real_plan/transit_validation.json`,
  `visualization_validation.json`, `building_ufh_summary.json`,
  `dev/ufh_spiral_validation/spiral_validation.json`.

## 4. Демо-задача этапа 1

Три агента независимо и на чтение исследуют, что мешает построению физических
улиток во всех доступных помещениях Test_01, каждый в своей ограниченной
области (без повторного полного аудита). Субагенты запускаются на
`deepseek-flash` для экономии квоты `deepseek-v4-pro High`; координатор
остаётся на `deepseek-v4-pro`.
