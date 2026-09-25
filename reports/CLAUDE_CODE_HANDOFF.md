# Claude Code Handoff — HomeAuraEngineeringAgent

Дата handoff: 2026-07-28. Режим подготовки: READ-ONLY. Этот документ создан
для передачи проекта новому агенту; исходники, Git index и история не менялись.

## 1. Проект и текущая цель

**Проект:** HomeAuraEngineeringAgent — локальный AI-агент автоматизации
проектирования инженерных систем.

**Текущая цель:** безопасно развивать read-only контракты и preview API вокруг
AutoCAD/MagiCAD-данных, сохраняя обратную совместимость и не переходя к
инженерной генерации/изменению DWG без отдельного подтверждения.

## 2. Архитектура

- `agent/` — Python 3.12 API и доменные/проектные модели на FastAPI/Pydantic.
- `agent/domain_models.py` и `agent/domain_adapter.py` — DOMAIN read-only
  слой над legacy rooms export.
- `agent/project_models.py` и `agent/project_foundation.py` — строгая
  `CanonicalProjectModel`, manifest reference и канонический JSON.
- `agent/api.py` — композиционный корень API, версия `0.6.0`.
- `autocad-plugin/HomeAura.AutoCAD.Agent/` — C# AutoCAD .NET plugin.
- `config/sheet_manifest.v1.json` — внешний manifest на 130 листов.
- `docs/ai_orchestration/` — локальный registry, task registry и handoff-
  prompts; каталог находится в working tree как untracked.
- `evidence/`, `bridge_reports/`, `reports/` — результаты проверок и передачи;
  их provenance нужно проверять по каждому конкретному файлу.

## 3. Реализовано

### AutoCAD plugin — VERIFIED

`HomeAura.AutoCAD.Agent` версии `1.2.0.0` заявляет:

- `HA_STATUS`, `HA_API_STATUS`;
- `HA_SYNC_MODEL`, `HA_SYNC_ROOMS`;
- `HA_DISCOVER_ROOM_BOUNDARIES`;
- `HA_EXPORT_ROOMS`, `HA_ANALYZE_MODEL`, `HA_FIND_REMOTE_OBJECT`;
- Boundary с XYZ/bulge/segment type, площадь, периметр, нормализация,
  самопересечения, point-in-polygon и диагностика unsupported types.

Файлы реализации: `Commands.cs`, `SyncCommands.cs`, `RoomSyncCommands.cs`,
`RoomExportCommands.cs`, `RoomDiscoveryCommands.cs`, `RoomBoundaryCommands.cs`,
`RoomGeometry.cs`, `AnalyzeCommands.cs`.

Runtime AutoCAD/MagiCAD и NETLOAD в этой handoff-подготовке не запускались —
**NEEDS_CHECK**.

### HA_SYNC_MODEL — VERIFIED (кодовый контракт), runtime — NEEDS_CHECK

Команда объявлена в `SyncCommands.cs`; она формирует snapshot объектов с
Handle, типом, слоем, центром и геометрическими границами. Фактический запуск
в AutoCAD и содержимое актуального snapshot должны быть проверены новым агентом.

### Python API — VERIFIED

- FastAPI app version `0.6.0` в `agent/api.py`.
- Existing health, project, rooms, analysis, IFC preview и DOMAIN preview
  routes.
- `POST /api/v1/projects/canonical/preview` — строгий local-only preview,
  canonical JSON, loopback/Host/Content-Type/Content-Length gates и no-I/O
  contract.
- DOMAIN schema literal version `1.0`.
- Legacy rooms formats `1.0` и `1.1` принимаются явно.
- PROJECT root models используют schema version `1.0`.

### Telegram / Bridge — NEEDS_CHECK for this repository

В этом репозитории есть `bridge_reports/` и orchestration documentation, но
рабочие Telegram/ChatGPT transport files находятся в отдельном
`C:\AI\HomeAuraOrchestrator`. Не переносить токены и не предполагать, что
bridge runtime доступен из этого проекта без отдельной проверки.

### Другие подтверждённые компоненты

- IFC read-only import/preview: `ifc_space_importer.py` и related API.
- Project foundation and strict preview: `project_foundation.py`,
  `project_models.py`.
- Work-mode schemas under `tools/work_mode/`.
- C# RoomGeometry test project under `tests/room_geometry/`.

## 4. Последние задачи перед передачей

- PROJECT-2B strict canonical project preview API.
- DOMAIN-1/DOMAIN-2B collision-safe identity and read-only preview.
- IFC Space read-only importer/preview.
- PROJECT/DOMAIN staged audits and contract-hardening reports.
- Orchestration package `HA-ORCH-CLINE-001`; parallel write execution remains
  not ready while standalone central schemas are not frozen.

## 5. Последние изменённые файлы

Git status captured with an explicit safe.directory override:

| Status | Path | Назначение |
|---|---|---|
| `M` | `README.md` | текущая документация проекта |
| `M` | `docs/COMPATIBILITY.md` | матрица совместимости |
| `M` | `docs/ROOM_GEOMETRY.md` | контракт геометрии помещений |
| `M` | `projects/Test_01/Test_01.bak` | пользовательский тестовый файл |
| `M` | `projects/Test_01/Test_01.dwg` | пользовательский DWG |
| `??` | `docs/ai_orchestration/` | orchestration registry/prompts/state |
| `??` | `bridge_reports/` | bridge evidence |
| `??` | `reports/*.txt` | audit/evidence reports |

`CLAUDE_CODE_HANDOFF.md` — новый untracked report, созданный этой передачей.
Он не staged и не committed.

## 6. Git output

Команды выполнялись только на чтение с `-c safe.directory=C:/AI/HomeAuraEngineeringAgent`.

### `git status --short` — VERIFIED

```text
 M README.md
 M docs/COMPATIBILITY.md
 M docs/ROOM_GEOMETRY.md
 M projects/Test_01/Test_01.bak
 M projects/Test_01/Test_01.dwg
?? bridge_reports/
?? docs/ai_orchestration/
?? reports/<много существующих untracked audit txt-файлов>
```

Точный полный список untracked report-файлов был длинным; получить его можно
без изменения состояния командой из раздела 14.

### `git branch` — VERIFIED

```text
feature/room-geometry
```

### `git log -5 --oneline` — VERIFIED

```text
c11205f feat(project): add strict canonical preview API
c33f5e8 feat(project): add canonical project foundation contract
bb48743 feat(domain): add hardened room preview endpoint
f086abf feat(domain): add collision-safe base contract
45c436d Add engineering project logic reference
```

### `git diff --stat` — PARTIAL / NEEDS_CHECK

Обычный `git diff --stat` не завершился: Git LFS не смог открыть временный
объект `.git/lfs/tmp/...` (`Access is denied`) при очистке filter-process для
`projects/Test_01/Test_01.dwg`. Это не исправлялось. Текстовый diff stat без
DWG/BAK можно получить командой из раздела 14.

## 7. Версии

| Область | Версия / состояние | Статус |
|---|---|---|
| Python API | `0.6.0` | VERIFIED |
| AutoCAD plugin | `1.2.0.0` | VERIFIED in AssemblyInfo/docs; runtime NEEDS_CHECK |
| rooms format | `1.1`, legacy `1.0` supported | VERIFIED in docs/code |
| DOMAIN schema | `1.0` | VERIFIED |
| PROJECT root schema | `1.0` | VERIFIED |
| sheet manifest | `schema_version=1.0`, `manifest_version=1.0`, id `homeaura-professional-engineering-130` | VERIFIED |
| orchestration registry | registry version `1.0` | VERIFIED in untracked registry |
| evidence package | multiple dated reports/evidence; no single frozen package identity established | NEEDS_CHECK |
| fastapi | `0.140.0` in `.venv` | VERIFIED |
| uvicorn | `0.51.0` in `.venv` | VERIFIED |
| numpy | `2.5.1` in `.venv` | VERIFIED |
| ifcopenshell | `0.8.5` in `.venv` | VERIFIED |

## 8. Intentionally uncommitted changes

The current state intentionally preserves owner-controlled unstaged changes in
README/compatibility/room geometry and the Test_01 DWG/BAK. Orchestration docs,
bridge reports and dated audit reports are intentionally untracked. Do not
stage, commit, reset, clean, filter-repo or publish them during initial review.

## 9. Files not to delete or regenerate

- `projects/Test_01/Test_01.dwg` and `Test_01.bak`;
- `projects/Test_01/exports/rooms/rooms.json`;
- `config/sheet_manifest.v1.json`;
- `evidence/` and dated audit reports;
- `docs/ai_orchestration/` registries/prompts/current state;
- existing AutoCAD plugin sources and version metadata;
- `.git/lfs` objects and LFS configuration;
- user-created bridge reports.

Do not regenerate manifests, ZIP/evidence bundles, schemas or DWG-derived
exports until the new agent identifies the exact source, version and owner
approval for that regeneration.

## 10. Risks

- Git LFS clean filter currently fails on the DWG due access denied in `.git/lfs/tmp`.
- Working tree has intentional staged-boundary ambiguity: tracked modifications
  and many untracked reports/docs coexist.
- Central standalone JSON schemas are not frozen; registry contains `MISSING` or
  `NOT_EXPORTED` entries and must not be filled by invention.
- AutoCAD/MagiCAD/NETLOAD runtime behavior is not currently verified.
- Bridge reports do not prove live Telegram or Claude/Cline connectivity.
- Existing project files are user-controlled and may contain engineering data;
  do not alter them as part of a code audit.
- Full API/plugin regression and current C# build were not rerun for this handoff.
- Remote GitHub state is not treated as current evidence.

## 11. Checks already performed

- `git status --short`, branch and last five commits — VERIFIED.
- JSON parsing/duplicate-key checks for orchestration registries — VERIFIED in
  the recorded current-state evidence; rerun before relying on untracked docs.
- Python test suites exist for rooms, IFC, DOMAIN and PROJECT — VERIFIED as
  present; current full execution NEEDS_CHECK.
- C# RoomGeometry test project exists — VERIFIED as present; execution NEEDS_CHECK.
- Secret-pattern scan in the prepared orchestration package — VERIFIED in the
  recorded evidence; do not treat it as a scan of all historical reports.
- API/plugin build and AutoCAD runtime — NEEDS_CHECK.

## 12. Remaining work

1. Reconfirm working-tree boundary and LFS failure without changing config.
2. Read the active orchestration registries and identify the single authorized
   task; do not execute untracked prompts automatically.
3. Export/freeze minimum standalone DOMAIN/PROJECT schemas only after owner
   approval.
4. Run focused Python tests and C# RoomGeometry tests.
5. Build the plugin only if Visual Studio/AutoCAD target prerequisites are
   confirmed.
6. Perform AutoCAD runtime checks (`HA_STATUS`, `HA_API_STATUS`,
   `HA_DISCOVER_ROOM_BOUNDARIES`) only with the owner present.
7. Reconcile evidence package identity and report paths.
8. Keep all external bridge/Telegram/Cline actions disabled until explicitly
   authorized.

## 13. First safe next step for Claude Code

Run the read-only commands in section 14, capture their output into a temporary
in-memory summary, and compare it with this handoff. Then produce a short
`NEEDS_CHECK` list. Do not edit files, stage changes, run migrations, execute
Git LFS cleanup, launch AutoCAD, or send external messages during this first
step.

## 14. Verification commands

All commands below are read-only. Run them from PowerShell; do not add a global
`safe.directory` entry. Use the explicit `-c` option shown.

```powershell
$root = 'C:\AI\HomeAuraEngineeringAgent'
git -c safe.directory=$root -C $root status --short
git -c safe.directory=$root -C $root branch --show-current
git -c safe.directory=$root -C $root log -5 --oneline
git -c safe.directory=$root -C $root diff --stat -- . ':!projects/Test_01/Test_01.dwg' ':!projects/Test_01/Test_01.bak'
Get-Content "$root\agent\api.py" -TotalCount 60
Get-Content "$root\docs\ai_orchestration\current_state.md" -TotalCount 180
Get-Content "$root\docs\ai_orchestration\contracts_registry.json"
Get-Content "$root\docs\ai_orchestration\task_registry.json"
& "$root\.venv\Scripts\python.exe" -m pytest -q "$root\tests"
dotnet --version
Get-Command msbuild,dotnet -ErrorAction SilentlyContinue
```

Before any write, migration, build artifact replacement, Git operation, AutoCAD
action, browser/Telegram action or external AI handoff, stop and request a
separate owner decision.

## 15. Local AI model policy — VERIFIED/NEEDS_CHECK

The workstation has Ollama `0.32.5` and local model `qwen2.5-coder:7b`.
Use this model as a local worker through the HomeAura Local Supervisor or a
dedicated Cline/Ollama adapter. The current Claude Pro session remains the
coordinator and architecture reviewer.

Do **not** set `ANTHROPIC_BASE_URL` directly to the default Ollama endpoint and
do not overwrite the current Claude Pro credentials. Claude Code documents
`ANTHROPIC_BASE_URL` as routing to a proxy/gateway that exposes the Anthropic
Messages format; a compatibility gateway must be verified before any local
model switch. A future local-only mode therefore requires:

1. an approved local Anthropic-Messages-compatible gateway in front of Ollama;
2. an allowlist limited to `127.0.0.1`;
3. a separate Claude Code profile/session, not the current Pro session;
4. a dry-run model discovery and one harmless test prompt;
5. a rollback command that unsets the custom endpoint.

Until those checks pass, local model work is **NEEDS_CHECK** and must remain
outside the active Claude Pro session. This preserves the local model goal
without risking credentials, unsupported API semantics or an opaque model
switch.
