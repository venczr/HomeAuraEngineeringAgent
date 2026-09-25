"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { buildCoverageRequest, CoveragePlan, EditorInput, Exclusion, parseEditorProject, serializeCoverageReport, serializeCoverageSvg, serializeEditorProject, supportedExteriorWalls, validateInput, WallSide } from "../../lib/floor-heating-contract";

const initialInput: EditorInput = {
  width_mm: 7000,
  height_mm: 3200,
  collector_x_mm: 3500,
  collector_y_mm: 1100,
  exterior_wall: "SOUTH",
  exclusions: [],
};

const routeColors = ["#38bdf8", "#fb923c", "#a78bfa"];
const sides: WallSide[] = supportedExteriorWalls;
const sideLabels: Record<WallSide, string> = { SOUTH: "Юг", NORTH: "Север", WEST: "Запад", EAST: "Восток" };
const diagnosticLabels: Record<string, string> = {
  COVERAGE_ESTIMATE_ONLY_FULL_COVERAGE_NOT_CLAIMED: "Покрытие рассчитано ориентировочно; полное покрытие не заявляется.",
  COVERAGE_REQUIRES_MORE_THAN_THREE_CIRCUITS: "Для этой комнаты требуется больше трёх контуров — за пределами MVP.",
  COVERAGE_EXCLUSION_CROSSES_ZONE_BOUNDARY: "Препятствие пересекает границу территорий контуров.",
};

function formatDiagnostic(value: string) {
  if (diagnosticLabels[value]) return diagnosticLabels[value];
  const [zone, code] = value.split(":", 2);
  return code ? `${zone}: ${diagnosticLabels[code] ?? code.replaceAll("_", " ").toLowerCase()}` : value.replaceAll("_", " ").toLowerCase();
}

function NumericField({ label, value, onChange, step = 100 }: { label: string; value: number; onChange: (value: number) => void; step?: number }) {
  return <label className="field"><span>{label}</span><div><input type="number" value={value} step={step} onChange={(event) => onChange(Number(event.target.value))} /><b>мм</b></div></label>;
}

type HouseRoom = { id: string; floor: "FLOOR_1_PLAN" | "ATTIC_PLAN"; label: string; status: string; geometry_status: string; strategy?: string; strategy_reason?: string; route_validation?: Array<Record<string, unknown>>; routes: number[][][]; route_ids?: string[]; global_boundary_mm: number[][]; lengths_mm: number[]; diagnostics: string[]; user_exit_mm?: number[]; user_exit_page?: number[]; user_exit_segment_mm?: number[][]; user_exit_segment_page?: number[][]; user_exit_status?: string };
type HouseProject = { project_id: string; source_plans: Record<string, string>; page_size: [number, number]; transforms: Record<string, { scale_mm_per_drawing_unit: number; origin_mm: [number, number] }>; defaults: { spacing_mm: number; wall_offset_mm: number; pipe: string; bend_radius_mm: number; maximum_circuit_length_mm: number }; rooms: HouseRoom[]; authority: string };

function HouseProjectEditor({ onBack }: { onBack: () => void }) {
  const [project, setProject] = useState<HouseProject | null>(null);
  const [floor, setFloor] = useState<HouseRoom["floor"]>("FLOOR_1_PLAN");
  const [selectedId, setSelectedId] = useState("");
  const [spacing, setSpacing] = useState(200);
  const [maxLength, setMaxLength] = useState(90000);
  const [layoutMode, setLayoutMode] = useState("AUTO");
  const [manifold, setManifold] = useState("SINGLE_MANIFOLD");
  const [showPlan, setShowPlan] = useState(true);
  const [showRoutes, setShowRoutes] = useState(true);
  const [markExit, setMarkExit] = useState(false);
  const [exitSegmentStart, setExitSegmentStart] = useState<number[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Исходные маршруты загружены из geometry-only пакета.");
  useEffect(() => { fetch("/plans/test01-project.json").then((r) => r.json()).then((data: HouseProject) => { const saved = window.localStorage.getItem("homeaura-test01-user-exits"); const exits = saved ? JSON.parse(saved) as Record<string, { user_exit_mm?: number[]; user_exit_page?: number[]; user_exit_segment_mm?: number[][]; user_exit_segment_page?: number[][]; user_exit_status?: string }> : {}; const merged = { ...data, rooms: data.rooms.map((room) => ({ ...room, ...(exits[room.id] ?? {}) })) }; setProject(merged); setSpacing(data.defaults.spacing_mm); setMaxLength(data.defaults.maximum_circuit_length_mm); const first = merged.rooms.find((room) => room.floor === "FLOOR_1_PLAN"); if (first) setSelectedId(first.id); }).catch(() => setMessage("Не удалось загрузить Test_01.")); }, []);
  useEffect(() => { if (!project) return; const exits = Object.fromEntries(project.rooms.filter((room) => room.user_exit_mm || room.user_exit_segment_mm).map((room) => [room.id, { user_exit_mm: room.user_exit_mm, user_exit_page: room.user_exit_page, user_exit_segment_mm: room.user_exit_segment_mm, user_exit_segment_page: room.user_exit_segment_page, user_exit_status: room.user_exit_status }])); window.localStorage.setItem("homeaura-test01-user-exits", JSON.stringify(exits)); }, [project]);
  const rooms = project?.rooms.filter((room) => room.floor === floor) ?? [];
  const selected = rooms.find((room) => room.id === selectedId) ?? rooms[0];
  const selectFloor = (nextFloor: HouseRoom["floor"]) => {
    setFloor(nextFloor);
    const nextRoom = project?.rooms.find((room) => room.floor === nextFloor);
    if (nextRoom) setSelectedId(nextRoom.id);
  };
  const transform = project?.transforms[floor];
  const toPage = (p: number[]) => transform ? [(p[0] - transform.origin_mm[0]) / transform.scale_mm_per_drawing_unit, (p[1] - transform.origin_mm[1]) / transform.scale_mm_per_drawing_unit] : p;
  const fromPage = (p: number[]) => transform ? [p[0] * transform.scale_mm_per_drawing_unit + transform.origin_mm[0], p[1] * transform.scale_mm_per_drawing_unit + transform.origin_mm[1]] : p;
  const markUserExit = (event: React.PointerEvent<SVGSVGElement>) => {
    if (!markExit || !project || !selected) return;
    const svg = event.currentTarget;
    const matrix = svg.getScreenCTM();
    if (!matrix) return;
    const point = svg.createSVGPoint(); point.x = event.clientX; point.y = event.clientY;
    const pagePoint = point.matrixTransform(matrix.inverse());
    const globalPoint = fromPage([pagePoint.x, pagePoint.y]);
    const next = [Math.round(globalPoint[0]), Math.round(globalPoint[1])];
    const page = [Math.round(pagePoint.x * 1000) / 1000, Math.round(pagePoint.y * 1000) / 1000];
    if (!exitSegmentStart) { setExitSegmentStart(next); setMessage("Начало проёма отмечено. Кликните вторую точку отрезка."); return; }
    const segment = [exitSegmentStart, next];
    const segmentPage = [toPage(exitSegmentStart), page];
    setProject((current) => current ? { ...current, rooms: current.rooms.map((room) => room.id === selected.id ? { ...room, user_exit_mm: next, user_exit_page: page, user_exit_segment_mm: segment, user_exit_segment_page: segmentPage, user_exit_status: "USER_SELECTED_OPENING_SEGMENT_UNVERIFIED" } : room) } : current);
    setExitSegmentStart(null); setMarkExit(false);
    setMessage(`Отрезок проёма сохранён: ${segment[0].join(", ")} → ${segment[1].join(", ")} мм. Конструктивное разрешение остаётся UNVERIFIED.`);
  };
  const clearUserExit = () => { setExitSegmentStart(null); setProject((current) => current ? { ...current, rooms: current.rooms.map((room) => room.id === selected?.id ? { ...room, user_exit_mm: undefined, user_exit_page: undefined, user_exit_segment_mm: undefined, user_exit_segment_page: undefined, user_exit_status: undefined } : room) } : current); };
  const saveHouseProject = () => { if (!project) return; const blob = new Blob([JSON.stringify(project, null, 2)], { type: "application/json" }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "Test_01-user-exits.json"; link.click(); URL.revokeObjectURL(url); };
  const recalculateBuildingTransit = async () => {
    if (!project) return;
    setBusy(true); setMessage("Проверяю общие транзитные трассы этажа…");
    try {
      const circuits = project.rooms.filter((room) => room.floor === floor).flatMap((room) => room.routes.map((route, index) => ({ circuit_id: `${room.id}/circuit-${index + 1}`, room_id: room.id, floor: room.floor, room_boundary_mm: room.global_boundary_mm, route_mm: route.map((point) => fromPage(point)), INTERNAL_PIPE_LENGTH: room.lengths_mm[index] ?? 0 })));
      const openings = Object.fromEntries(project.rooms.filter((room) => room.floor === floor && room.user_exit_segment_mm).map((room) => [room.id, { segment_mm: room.user_exit_segment_mm }]));
      const response = await fetch("/api/floor-heating/building-preview", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ project_id: "Test_01", circuits, openings }) });
      const result = await response.json(); if (!response.ok) throw new Error(result?.detail?.message ?? "маршрутизатор этажа отклонил запрос");
      const unresolved = result.circuits.filter((item: { status: string }) => item.status === "UNVERIFIED").length;
      setMessage(`Общий расчёт: ${result.circuits.length} контуров; ${unresolved} требуют отрезок проёма и полигон коридора. MANIFOLD_CONNECTED остаётся UNVERIFIED.`);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Общий расчёт не выполнен."); } finally { setBusy(false); }
  };
  const recalculate = async () => {
    if (!project || !selected) return;
    setBusy(true); setMessage("Пересчитываю выбранное помещение локальным ядром…");
    try {
      const boundary = selected.global_boundary_mm;
      const minX = Math.min(...boundary.map((p) => p[0])); const minY = Math.min(...boundary.map((p) => p[1]));
      const points = boundary.map((p) => ({ x_mm: Math.round(p[0] - minX), y_mm: Math.round(p[1] - minY) }));
      const preferredExitLocal = selected.user_exit_mm ? [Math.round(selected.user_exit_mm[0] - minX), Math.round(selected.user_exit_mm[1] - minY)] : undefined;
      const preferredExitSegmentLocal = selected.user_exit_segment_mm?.map((point) => [Math.round(point[0] - minX), Math.round(point[1] - minY)]);
      const zoneResponse = layoutMode !== "MEANDER" ? await fetch("/api/floor-heating/zone-preview", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ project_id: "Test_01", room_id: selected.id, boundary: { points }, mode: layoutMode, spacing_mm: spacing, wall_offset_mm: 100, turn_radius_mm: 80, maximum_zones: 3, preferred_exit_mm: preferredExitLocal, preferred_exit_segment_mm: preferredExitSegmentLocal }) }) : null;
      if (zoneResponse) {
        if (!zoneResponse.ok) throw new Error("ядро зонирования отклонило запрос");
        const zonePlan = await zoneResponse.json();
        const candidate = zonePlan.recommended;
        if (candidate?.routes?.length) {
          const nextRoutes = candidate.routes.map((zone: { route_mm: number[][] }) => zone.route_mm.map((p) => toPage([p[0] + minX, p[1] + minY])));
          const nextLengths = candidate.routes.map((zone: { length_mm: number }) => zone.length_mm);
          const routeIds = candidate.routes.map((zone: { route_id?: string }, index: number) => zone.route_id ?? `${zonePlan.strategy?.toLowerCase() ?? "route"}-${index + 1}`);
          const routeStatus = zonePlan.strategy === "UNRESOLVED" ? "UNRESOLVED" : "RECALCULATED_PREVIEW";
          setProject((current) => current ? { ...current, rooms: current.rooms.map((room) => room.id === selected.id ? { ...room, routes: nextRoutes, route_ids: routeIds, lengths_mm: nextLengths, strategy: zonePlan.strategy, strategy_reason: zonePlan.strategy_reason, route_validation: candidate.routes, status: routeStatus, diagnostics: [...(zonePlan.rejected_candidates ?? []), ...(candidate.diagnostics ?? [])] } : room) } : current);
          setMessage(`${zonePlan.strategy}: ${nextRoutes.length} самостоятельных маршрута; длины ${nextLengths.map((length: number) => `${(length / 1000).toFixed(1)} м`).join(" + ")}. Выход ${selected.user_exit_mm ? "учтён геометрически" : "не задан"}; подключение UNVERIFIED.`);
          return;
        }
        throw new Error(`${layoutMode} не сформировал допустимую раскладку: ${(zonePlan.rejected_candidates ?? zonePlan.diagnostics ?? []).join(", ")}`);
      }
      const response = await fetch("/api/floor-heating/coverage-preview", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ schema_version: "1.0", project_id: "Test_01", room_id: selected.id, boundary: { points }, exclusion_zones: [], collector_point: { x_mm: Math.max(100, Math.round((Math.max(...points.map((p) => p.x_mm)) - Math.min(...points.map((p) => p.x_mm))) / 2)), y_mm: 100 }, wall_offset_mm: 100, spacing_mm: spacing as 100 | 150 | 200, minimum_circuit_length_mm: 1, maximum_circuit_length_mm: maxLength, turn_radius_mm: 80, routing_mode: "non_crossing_visual", requested_circuit_count: 1, field_spacing_mm: spacing as 100 | 150 | 200, perimeter_spacing_mm: 100, perimeter_band_depth_mm: 1000, perimeter_priority_mode: true, installation_grid_spacing_mm: 100, exterior_wall_segments: [{ reference: `${selected.id}-boundary-edge-0`, start: points[0], end: points[1] }] }) });
      if (!response.ok) throw new Error("ядро отклонило запрос");
      const next = await response.json();
      const nextRoutes = (next.circuit_routes ?? []).map((route: { polyline: { x_mm: number; y_mm: number }[] }) => route.polyline.map((p) => toPage([p.x_mm + minX, p.y_mm + minY])));
      if (nextRoutes.length) {
        setProject((current) => current ? { ...current, rooms: current.rooms.map((room) => room.id === selected.id ? { ...room, routes: nextRoutes, lengths_mm: (next.circuit_routes ?? []).map((route: { length_mm: number }) => route.length_mm), status: next.status === "ok" ? "RECALCULATED_PREVIEW" : "PARTIAL" } : room) } : current);
        setMessage(`Готово: ${next.circuit_routes?.length ?? 0} маршрут(а), параметры ${spacing} мм / ${Math.round(maxLength / 1000)} м.`);
      } else {
        setMessage(`Маршрут не заменён: ${next.diagnostics?.join(", ") ?? "ядро не сформировало допустимую геометрию"}. Исходная геометрия сохранена.`);
      }
    } catch (error) { setMessage(error instanceof Error ? error.message : "Расчёт не выполнен."); } finally { setBusy(false); }
  };
  if (!project) return <main className="app-shell"><div className="empty-canvas"><b>Загрузка Test_01…</b></div></main>;
  return <main className="app-shell house-editor"><header className="topbar"><div className="brand"><span className="brand-mark">H</span><div><strong>HomeAura</strong><small>Test_01 · планировщик тёплого пола</small></div></div><div className="project-pill"><span>Проект</span><b>Test_01</b><button onClick={onBack}>Комната MVP</button><button onClick={saveHouseProject}>Сохранить проект</button></div><div className="status status-partial"><span />GEOMETRY PREVIEW</div></header><section className="house-workspace"><aside className="panel left-panel"><div className="panel-title"><span>01</span><div><b>Исходный план</b><small>Оригинальный PDF как растровый фон</small></div></div><div className="segmented floor-tabs"><button className={floor === "FLOOR_1_PLAN" ? "active" : ""} onClick={() => selectFloor("FLOOR_1_PLAN")}>1 этаж</button><button className={floor === "ATTIC_PLAN" ? "active" : ""} onClick={() => selectFloor("ATTIC_PLAN")}>Мансарда</button></div><label className="field house-select"><span>Помещение</span><select value={selected?.id ?? ""} onChange={(event) => setSelectedId(event.target.value)}>{rooms.map((room) => <option key={room.id} value={room.id}>{room.label}</option>)}</select></label><div className="workflow-step"><b>Шаг 1</b><span>Выберите этаж и помещение</span></div><div className="panel-title section"><span>02</span><div><b>Параметры генерации</b><small>Шаг 2 · измените параметры при необходимости</small></div></div><label className="field house-select"><span>Шаг укладки</span><select value={spacing} onChange={(event) => setSpacing(Number(event.target.value))}><option value={100}>100 мм</option><option value={150}>150 мм</option><option value={200}>200 мм</option></select></label><NumericField label="Предел контура" value={maxLength} onChange={setMaxLength} step={1000}/><label className="field house-select"><span>Тип раскладки</span><select value={layoutMode} onChange={(event) => setLayoutMode(event.target.value)}><option value="AUTO">AUTO — приоритет улитки</option><option value="SPIRAL">SPIRAL — только улитка</option><option value="HYBRID">HYBRID — улитка + сложные зоны</option><option value="MEANDER">MEANDER — ручной выбор</option></select></label><label className="field house-select"><span>Коллекторный сценарий</span><select value={manifold} onChange={(event) => setManifold(event.target.value)}><option value="SINGLE_MANIFOLD">Один в котельной</option><option value="TWO_MANIFOLDS">По коллектору на этаж</option></select></label><div className="workflow-step"><b>Шаг 3</b><span>Проём можно указать двумя кликами на плане</span></div><button className={`secondary-button exit-button ${markExit ? "active" : ""}`} onClick={() => { setExitSegmentStart(null); setMarkExit((value) => !value); }}>{markExit ? (exitSegmentStart ? "Теперь кликните конец проёма" : "Теперь кликните начало проёма") : "＋ Указать отрезок дверного проёма"}</button>{selected?.user_exit_mm && <div className="exit-selection"><small>Выход: {selected.user_exit_mm[0]}, {selected.user_exit_mm[1]} мм · {selected.user_exit_status}</small><button className="secondary-button" onClick={clearUserExit}>Удалить отметку</button></div>}<div className="assumption-card"><span className="dot orange"/><div><b>Труба {project.defaults.pipe} · R{project.defaults.bend_radius_mm}</b><small>Предварительные инженерные параметры</small></div></div><button className="primary-button" disabled={busy || !selected} onClick={() => void recalculate()}>{busy ? "Расчёт…" : "Рассчитать помещение"}<span>→</span></button><button className="secondary-button transit-button" disabled={busy} onClick={() => void recalculateBuildingTransit()}>Рассчитать транзит этажа</button><div className="message-card">{message}</div><p className="hint">Подключение к коллектору остаётся UNVERIFIED до подтверждения проёма и трассы.</p>{selected?.label.startsWith("2 /") && <div className="message-card stair-note"><b>Коридор и лестница</b><br/>Первые 3 ступени: зона контакта с полом и исключение. Остальная площадь вокруг лестницы считается полезной для раскладки; проходы труб через ступени не разрешены.</div>}{selected?.door_note && <div className="message-card stair-note">{selected.door_note}</div>}</aside><section className="house-canvas-panel"><div className="canvas-toolbar"><div><button className="tool active" onClick={() => setShowPlan((value) => !value)}>План</button><button className="tool active" onClick={() => setShowRoutes((value) => !value)}>Трубы</button></div><div className="legend"><span><i className="line" style={{ background: "#d92d20" }}/>Подача</span><span><i className="line" style={{ background: "#1570ef" }}/>Обратка</span></div></div><div className="house-canvas-wrap"><svg onMouseUp={markUserExit} viewBox={`0 0 ${project.page_size[0]} ${project.page_size[1]}`} preserveAspectRatio="xMidYMid meet" role="img" aria-label="Исходный план Test_01 с раскладкой"><rect width="595" height="842" fill="#fff"/>{showPlan && <image href={project.source_plans[floor]} x="0" y="0" width="595" height="842"/>}{selected?.user_exit_page && <g>{selected.user_exit_segment_page &&
<polyline points={selected.user_exit_segment_page.map((p) => p.join(",")).join(" ")} fill="none" stroke="#f59e0b" strokeWidth="3" strokeDasharray="5 3"/>}<circle cx={selected.user_exit_page[0]} cy={selected.user_exit_page[1]} r="4" fill="#f59e0b" stroke="#fff" strokeWidth="1"/><text x={selected.user_exit_page[0] + 6} y={selected.user_exit_page[1] - 5} fontSize="6" fill="#b45309">проём · UNVERIFIED</text></g>}{showRoutes && rooms.map((room) => room.routes.map((route, index) => { const mid = Math.max(1, Math.floor(route.length / 2)); return <g key={`${room.id}-${index}`} opacity={selected?.id === room.id ? 1 : .42}>
<polyline points={route.slice(0, mid + 1).map((p) => p.join(",")).join(" ")} fill="none" stroke="#d92d20" strokeWidth="1.4"/>
<polyline points={route.slice(mid).map((p) => p.join(",")).join(" ")} fill="none" stroke="#1570ef" strokeWidth="1.4"/><circle cx={route[0]?.[0]} cy={route[0]?.[1]} r="2.4" fill="#16a34a"/><circle cx={route[route.length - 1]?.[0]} cy={route[route.length - 1]?.[1]} r="2.4" fill="#7c3aed"/><text x={(route[0]?.[0] ?? 0) + 4} y={(route[0]?.[1] ?? 0) - 3} fontSize="5" fill="#166534">{room.route_ids?.[index] ?? `C${index + 1}`}</text></g>; }))}{selected?.global_boundary_mm?.length > 2 && 
<polyline points={selected.global_boundary_mm.map((p) => toPage(p)).map((p) => p.join(",")).join(" ")} fill="none" stroke="#f59e0b" strokeWidth="1.2" strokeDasharray="5 3"/>}</svg><div className="house-caption">{selected?.label} · {selected?.lengths_mm.map((length) => `${(length / 1000).toFixed(1)} м`).join(" + ") || "маршрут не сформирован"} · {selected?.status}</div></div></section><aside className="panel right-panel"><div className="panel-title"><span>03</span><div><b>Проверки</b><small>{project.authority}</small></div></div><div className="metrics"><div><span>Помещение</span><b>{selected?.label.split(";")[0] ?? "—"}</b></div><div><span>Маршрутов</span><b>{selected?.routes.length ?? 0}</b></div><div><span>Стратегия</span><b>{selected?.strategy ?? "—"}</b></div><div><span>Подключение</span><b>UNVERIFIED</b></div></div><div className="limitations"><b>Статусы</b><p>GEOMETRY_VALID: {selected?.status === "SKIPPED_GEOMETRY_UNRESOLVED" ? "UNVERIFIED" : selected?.route_validation?.length ? (selected.route_validation.every((route) => route.GEOMETRY_VALID !== false) ? "VALID" : "INVALID") : "UNVERIFIED"}</p><p>TOPOLOGY_VALID: {selected?.route_validation?.length ? (selected.route_validation.every((route) => route.TOPOLOGY_VALID !== false) ? "VALID" : "INVALID") : "UNVERIFIED"}</p><p>BEND_VALID: {selected?.route_validation?.length ? (selected.route_validation.every((route) => route.BEND_VALID !== false) ? "VALID" : "INVALID") : "UNVERIFIED"}</p><p>PIPE_LENGTH_VALID: {selected?.lengths_mm.length ? (selected.lengths_mm.every((length) => length <= maxLength) ? "VALID" : "INVALID") : "UNVERIFIED"}</p><p>ENDPOINT_ACCESS_VALID: {selected?.route_validation?.length ? (selected.route_validation.every((route) => route.ENDPOINT_ACCESS_VALID !== false) ? "VALID" : "INVALID") : "UNVERIFIED"}</p><p>MANIFOLD_CONNECTED: UNVERIFIED</p><p>Причина / ограничения: {selected?.strategy_reason ?? selected?.diagnostics?.join("; ") ?? "—"}</p><p>Сценарий: {manifold === "SINGLE_MANIFOLD" ? "один коллектор" : "два коллектора"}</p></div><button className="secondary-button" onClick={() => window.open("/plans/Test_01_floor_1_plan.png", "_blank")}>Открыть план PNG</button></aside></section></main>;
}

export function HomeAuraEditor() {
  const [houseMode, setHouseMode] = useState(false);
  const [input, setInput] = useState<EditorInput>(initialInput);
  const [plan, setPlan] = useState<CoveragePlan | null>(null);
  const [status, setStatus] = useState<"DRAFT" | "STALE" | "CALCULATING" | "VALIDATED" | "PARTIAL" | "IMPOSSIBLE" | "ERROR">("DRAFT");
  const [transportError, setTransportError] = useState("");
  const [showGrid, setShowGrid] = useState(true);
  const [activeTool, setActiveTool] = useState<"SELECT" | "ANCHOR">("SELECT");
  const requestNumber = useRef(0);
  const fileInput = useRef<HTMLInputElement>(null);
  const drawing = useRef<SVGSVGElement>(null);
  const errors = useMemo(() => validateInput(input), [input]);

  const update = (patch: Partial<EditorInput>) => {
    requestNumber.current += 1;
    setInput((current) => ({ ...current, ...patch }));
    setStatus((current) => plan || current === "CALCULATING" ? "STALE" : "DRAFT");
  };

  const calculate = async () => {
    if (errors.length) return;
    const sequence = ++requestNumber.current;
    const requestBody = JSON.stringify(buildCoverageRequest(input));
    setStatus("CALCULATING");
    setTransportError("");
    try {
      const response = await fetch("/api/floor-heating/coverage-preview", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: requestBody,
      });
      const body = await response.json();
      if (sequence !== requestNumber.current) return;
      if (!response.ok) throw new Error(body?.detail?.message ?? "Расчёт не выполнен.");
      const nextPlan = body as CoveragePlan;
      setPlan(nextPlan);
      setStatus(nextPlan.status === "impossible" ? "IMPOSSIBLE" : nextPlan.full_coverage_claimed ? "VALIDATED" : "PARTIAL");
    } catch (error) {
      if (sequence !== requestNumber.current) return;
      setPlan(null);
      setTransportError(error instanceof Error ? error.message : "Не удалось связаться с ядром.");
      setStatus("ERROR");
    }
  };

  const addExclusion = () => {
    const zone: Exclusion = { id: `zone-${Date.now()}`, x_mm: 1500, y_mm: 1200, width_mm: 400, height_mm: 400 };
    update({ exclusions: [...input.exclusions, zone] });
  };

  const updateExclusion = (id: string, patch: Partial<Exclusion>) => update({ exclusions: input.exclusions.map((zone) => zone.id === id ? { ...zone, ...patch } : zone) });
  const downloadArtifact = (content: string, filename: string, type: string) => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  };
  const saveProject = () => downloadArtifact(serializeEditorProject(input), `homeaura-${input.width_mm}x${input.height_mm}.json`, "application/json");
  const openProject = async (file: File | undefined) => {
    if (!file) return;
    try {
      const nextInput = parseEditorProject(await file.text());
      requestNumber.current += 1;
      setInput(nextInput);
      setPlan(null);
      setTransportError("");
      setStatus("DRAFT");
    } catch (error) {
      setTransportError(error instanceof Error ? error.message : "Не удалось открыть проект.");
      setStatus("ERROR");
    } finally {
      if (fileInput.current) fileInput.current.value = "";
    }
  };
  const placeAnchor = (event: React.PointerEvent<SVGSVGElement>) => {
    if (activeTool !== "ANCHOR" || !drawing.current) return;
    const matrix = drawing.current.getScreenCTM();
    if (!matrix) return;
    const point = drawing.current.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const svgPoint = point.matrixTransform(matrix.inverse());
    const snap = (value: number, maximum: number) => Math.max(100, Math.min(Math.round(value / 100) * 100, maximum - 100));
    update({ collector_x_mm: snap(svgPoint.x, input.width_mm), collector_y_mm: snap(input.height_mm - svgPoint.y, input.height_mm) });
    setActiveTool("SELECT");
  };
  const scaleRoom = `-350 -500 ${input.width_mm + 700} ${input.height_mm + 850}`;
  const gridXs = Array.from({ length: Math.floor(input.width_mm / 100) + 1 }, (_, i) => i * 100);
  const gridYs = Array.from({ length: Math.floor(input.height_mm / 100) + 1 }, (_, i) => i * 100);

  if (houseMode) return <HouseProjectEditor onBack={() => setHouseMode(false)} />;
  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">H</span><div><strong>HomeAura</strong><small>Floor Heating Editor · MVP</small></div></div>
        <div className="project-pill"><span>Проект</span><b>Локальный</b><button onClick={() => setHouseMode(true)}>Дом Test_01</button><button onClick={() => fileInput.current?.click()}>Открыть</button><button onClick={saveProject}>Сохранить</button><i /> <span>Комната</span><b>{input.width_mm} × {input.height_mm}</b><input ref={fileInput} type="file" accept="application/json,.json" hidden onChange={(event) => void openProject(event.target.files?.[0])}/></div>
        <div className={`status status-${status.toLowerCase()}`}><span />{status === "PARTIAL" ? "ВАЛИДНАЯ ГЕОМЕТРИЯ · ЧАСТИЧНОЕ ПОКРЫТИЕ" : status}</div>
      </header>

      <section className="workspace">
        <aside className="panel left-panel">
          <div className="panel-title"><span>01</span><div><b>Геометрия помещения</b><small>Канонические единицы — миллиметры</small></div></div>
          <div className="fields-grid">
            <NumericField label="Ширина" value={input.width_mm} onChange={(width_mm) => update({ width_mm })} />
            <NumericField label="Длина" value={input.height_mm} onChange={(height_mm) => update({ height_mm })} />
          </div>
          <div className="section-label">Наружная стена · MVP поддерживает Юг/Север</div>
          <div className="segmented">{sides.map((side) => <button key={side} className={input.exterior_wall === side ? "active" : ""} onClick={() => update({ exterior_wall: side })}>{sideLabels[side]}</button>)}</div>
          <div className="assumption-card"><span className="dot orange"/><div><b>Периметральная зона</b><small>Глубина 1000 мм · шаг 100 мм</small></div></div>

          <div className="panel-title section"><span>02</span><div><b>Якорь маршрута</b><small>Не физическая модель коллектора</small></div></div>
          <div className="fields-grid">
            <NumericField label="Координата X" value={input.collector_x_mm} onChange={(collector_x_mm) => update({ collector_x_mm })} />
            <NumericField label="Координата Y" value={input.collector_y_mm} onChange={(collector_y_mm) => update({ collector_y_mm })} />
          </div>
          <p className="hint">Точка на сетке 100 мм задаёт желаемую ось входа. Планировщик проецирует её в каждую территорию; концевые точки труб создаёт только ядро.</p>

          <div className="panel-title section"><span>03</span><div><b>Препятствия</b><small>Текущий движок проверяет, но не обходит</small></div></div>
          {input.exclusions.map((zone, index) => <div className="exclusion-editor" key={zone.id}>
            <div><b>Препятствие {index + 1}</b><button aria-label="Удалить препятствие" onClick={() => update({ exclusions: input.exclusions.filter((item) => item.id !== zone.id) })}>×</button></div>
            <div className="mini-grid">
              <NumericField label="X" value={zone.x_mm} onChange={(x_mm) => updateExclusion(zone.id, { x_mm })} />
              <NumericField label="Y" value={zone.y_mm} onChange={(y_mm) => updateExclusion(zone.id, { y_mm })} />
              <NumericField label="Ширина" value={zone.width_mm} onChange={(width_mm) => updateExclusion(zone.id, { width_mm })} />
              <NumericField label="Высота" value={zone.height_mm} onChange={(height_mm) => updateExclusion(zone.id, { height_mm })} />
            </div>
          </div>)}
          <button className="secondary-button" onClick={addExclusion}>＋ Добавить прямоугольное препятствие</button>
        </aside>

        <section className="canvas-panel">
          <div className="canvas-toolbar"><div><button className={`tool ${activeTool === "SELECT" ? "active" : ""}`} onClick={() => setActiveTool("SELECT")}>↖ <span>Выбор</span></button><button className={`tool ${activeTool === "ANCHOR" ? "active" : ""}`} onClick={() => setActiveTool("ANCHOR")}>⊕ <span>Якорь</span></button><button className="tool" onClick={() => setShowGrid((value) => !value)}>⌗ <span>Сетка</span></button></div><div className="legend">{plan?.circuit_routes.map((route, index) => <span key={route.id}><i className="line" style={{background: routeColors[index % routeColors.length]}}/>Контур {index + 1}</span>)}<span><i className="wall"/>Наружная стена</span></div></div>
          <div className={`canvas-wrap ${status === "STALE" ? "is-stale" : ""}`}>
            <svg ref={drawing} role="img" aria-label="Инженерный план комнаты и контуров" viewBox={scaleRoom} preserveAspectRatio="xMidYMid meet" data-tool={activeTool} onPointerDown={placeAnchor}>
              <g transform={`translate(0 ${input.height_mm}) scale(1 -1)`}>
              <rect x="0" y="0" width={input.width_mm} height={input.height_mm} className="room-fill" />
              {showGrid && <g className="grid-lines">{gridXs.map((x) => <line key={`x${x}`} x1={x} y1="0" x2={x} y2={input.height_mm} />)}{gridYs.map((y) => <line key={`y${y}`} x1="0" y1={y} x2={input.width_mm} y2={y} />)}</g>}
              <rect x="0" y={input.exterior_wall === "NORTH" ? input.height_mm - 1000 : 0} width={input.exterior_wall === "WEST" || input.exterior_wall === "EAST" ? 1000 : input.width_mm} height={input.exterior_wall === "WEST" || input.exterior_wall === "EAST" ? input.height_mm : 1000} className="perimeter-band" transform={input.exterior_wall === "EAST" ? `translate(${input.width_mm - 1000} 0)` : undefined} />
              <rect x="0" y="0" width={input.width_mm} height={input.height_mm} className="room-boundary" />
              <line x1={input.exterior_wall === "EAST" ? input.width_mm : 0} y1={input.exterior_wall === "NORTH" ? input.height_mm : 0} x2={input.exterior_wall === "WEST" ? 0 : input.width_mm} y2={input.exterior_wall === "SOUTH" ? 0 : input.height_mm} className={`exterior exterior-${input.exterior_wall.toLowerCase()}`} />
              {input.exclusions.map((zone) => <g key={zone.id}><rect x={zone.x_mm - 100} y={zone.y_mm - 100} width={zone.width_mm + 200} height={zone.height_mm + 200} className="clearance"/><rect x={zone.x_mm} y={zone.y_mm} width={zone.width_mm} height={zone.height_mm} className="exclusion"/></g>)}
              {plan?.circuit_routes.map((route, index) => <polyline key={route.id} points={route.polyline.map((point) => `${point.x_mm},${point.y_mm}`).join(" ")} className="route" style={{ stroke: routeColors[index % routeColors.length] }} data-route-id={route.id} />)}
              {plan?.zones.map((zone) => <circle key={zone.zone_id} cx={zone.route_anchor_point.x_mm} cy={zone.route_anchor_point.y_mm} r="45" className="projected-anchor" />)}
              <g className="collector-anchor"><circle cx={input.collector_x_mm} cy={input.collector_y_mm} r="70"/><line x1={input.collector_x_mm - 120} y1={input.collector_y_mm} x2={input.collector_x_mm + 120} y2={input.collector_y_mm}/><line x1={input.collector_x_mm} y1={input.collector_y_mm - 120} x2={input.collector_x_mm} y2={input.collector_y_mm + 120}/></g>
              </g>
            </svg>
            {activeTool === "ANCHOR" && <div className="tool-hint">Щёлкните по узлу сетки, чтобы задать желаемую ось входа</div>}
            {status === "STALE" && <div className="stale-banner">Геометрия устарела — выполните новый расчёт</div>}
            {!plan && <div className="empty-canvas"><b>Готово к расчёту</b><span>Размеры комнаты и инженерные допущения уже заданы.</span></div>}
          </div>
        </section>

        <aside className="panel right-panel">
          <div className="panel-title"><span>04</span><div><b>Инженерный расчёт</b><small>Источник — локальное ядро HomeAura</small></div></div>
          <div className="metrics"><div><span>Отапливаемая площадь</span><b>{plan ? (plan.heated_area_mm2 / 1_000_000).toFixed(1) : (input.width_mm * input.height_mm / 1_000_000).toFixed(1)} м²</b></div><div><span>Контуров</span><b>{plan?.required_circuit_count ?? "—"}</b></div><div><span>Оценка покрытия</span><b>{plan ? `${(plan.coverage_ratio * 100).toFixed(1)}%` : "—"}</b></div><div><span>Сетка</span><b>100 мм</b></div></div>
          <div className="route-list">{plan?.circuit_routes.map((route, index) => <article key={route.id}>
            <div className="route-head"><span style={{ background: routeColors[index % routeColors.length] }}>C{index + 1}</span><div><b>Контур {index + 1}</b><small>{(route.length_mm / 1000).toFixed(1)} м из 40–80 м</small></div><em className={route.validation.valid ? "pass" : "fail"}>{route.validation.valid ? "PASS" : "REWORK"}</em></div>
            <div className="validation-grid"><span>Связность <b>{route.validation.connected ? "✓" : "×"}</b></span><span>Пересечения <b>{route.validation.self_intersection ? "×" : "0"}</b></span><span>Ветвления <b>{route.validation.branches ? "×" : "0"}</b></span><span>Шаг <b>{route.validation.step_valid ? "✓" : "×"}</b></span><span>Граница <b>{route.validation.inside_boundary ? "✓" : "×"}</b></span><span>Препятствия <b>{route.validation.exclusion_clear ? "✓" : "×"}</b></span><span>Длина <b>{route.validation.length_valid ? "✓" : "×"}</b></span><span>Концы <b>{route.validation.endpoints_valid ? "✓" : "×"}</b></span></div>
          </article>)}</div>
          {(errors.length > 0 || Boolean(transportError) || (plan?.diagnostics.length ?? 0) > 0) && <div className="diagnostics"><b>Диагностика</b>{errors.map((error) => <p key={error}>{error}</p>)}{transportError && <p>{transportError}</p>}{plan?.diagnostics.map((item) => <p key={item}>{formatDiagnostic(item)}</p>)}</div>}
          <div className="limitations"><b>Границы MVP</b><p>Не рассчитываются гидравлика, насос, смесительный узел, диаметр трубы и нормативное соответствие.</p><p>Препятствие может привести к <strong>IMPOSSIBLE</strong>: автоматический обход ещё не реализован.</p></div>
          <button className="primary-button" disabled={errors.length > 0 || status === "CALCULATING"} onClick={calculate}>{status === "CALCULATING" ? "Расчёт…" : "Рассчитать контуры"}<span>→</span></button>
          <div className="export-actions"><button disabled={!plan || status === "STALE" || status === "ERROR" || status === "IMPOSSIBLE"} onClick={() => plan && downloadArtifact(serializeCoverageSvg(input, plan), `homeaura-${plan.plan_digest.slice(0, 12)}.svg`, "image/svg+xml")}>Скачать SVG</button><button disabled={!plan || status === "STALE" || status === "ERROR" || status === "IMPOSSIBLE"} onClick={() => plan && downloadArtifact(serializeCoverageReport(input, plan), `homeaura-${plan.plan_digest.slice(0, 12)}-report.json`, "application/json")}>Скачать отчёт</button></div>
          <small className="digest">{plan ? `Digest ${plan.plan_digest.slice(0, 16)}…` : "Результат ещё не рассчитан"}</small>
        </aside>
      </section>
    </main>
  );
}



