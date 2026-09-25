export type Point = { x_mm: number; y_mm: number };
export type WallSide = "SOUTH" | "NORTH" | "WEST" | "EAST";
export const supportedExteriorWalls: WallSide[] = ["SOUTH", "NORTH"];

export type Exclusion = { id: string; x_mm: number; y_mm: number; width_mm: number; height_mm: number };

export type EditorInput = {
  width_mm: number;
  height_mm: number;
  collector_x_mm: number;
  collector_y_mm: number;
  exterior_wall: WallSide;
  exclusions: Exclusion[];
};

export type EditorProjectFile = {
  schema_version: "1.0";
  kind: "homeaura-floor-heating-editor-input";
  units: "mm";
  input: EditorInput;
};

export type RouteValidation = {
  connected: boolean;
  self_intersection: boolean;
  branches: boolean;
  step_valid: boolean;
  length_valid: boolean;
  inside_boundary: boolean;
  exclusion_clear: boolean;
  endpoints_valid: boolean;
  valid: boolean;
};

export type CircuitRoute = {
  id: string;
  polyline: Point[];
  length_mm: number;
  collector_supply_point: Point;
  collector_return_point: Point;
  validation: RouteValidation;
};

export type CoveragePlan = {
  status: "planned" | "partial" | "impossible";
  required_circuit_count: number;
  collector_port_count: number;
  heated_area_mm2: number;
  estimated_coverage_mm2: number;
  coverage_ratio: number;
  full_coverage_claimed: boolean;
  zones: Array<{ zone_id: string; route_anchor_point: Point }>;
  circuit_routes: CircuitRoute[];
  diagnostics: string[];
  plan_digest: string;
};

const point = (x_mm: number, y_mm: number): Point => ({ x_mm, y_mm });

export function buildCoverageRequest(input: EditorInput) {
  const { width_mm: w, height_mm: h } = input;
  const walls: Record<WallSide, [Point, Point]> = {
    SOUTH: [point(0, 0), point(w, 0)],
    NORTH: [point(0, h), point(w, h)],
    WEST: [point(0, 0), point(0, h)],
    EAST: [point(w, 0), point(w, h)],
  };
  return {
    schema_version: "1.0",
    project_id: "homeaura-editor",
    room_id: `room-${w}x${h}`,
    boundary: { points: [point(0, 0), point(w, 0), point(w, h), point(0, h), point(0, 0)] },
    exclusion_zones: input.exclusions.map((zone) => ({
      points: [
        point(zone.x_mm, zone.y_mm),
        point(zone.x_mm + zone.width_mm, zone.y_mm),
        point(zone.x_mm + zone.width_mm, zone.y_mm + zone.height_mm),
        point(zone.x_mm, zone.y_mm + zone.height_mm),
        point(zone.x_mm, zone.y_mm),
      ],
    })),
    collector_point: point(input.collector_x_mm, input.collector_y_mm),
    wall_offset_mm: 100,
    spacing_mm: 200,
    minimum_circuit_length_mm: 40000,
    maximum_circuit_length_mm: 80000,
    turn_radius_mm: 100,
    field_spacing_mm: 200,
    perimeter_spacing_mm: 100,
    perimeter_band_depth_mm: 1000,
    installation_grid_spacing_mm: 100,
    perimeter_priority_mode: true,
    exterior_wall_segments: [{ reference: `exterior-${input.exterior_wall.toLowerCase()}`, start: walls[input.exterior_wall][0], end: walls[input.exterior_wall][1] }],
  };
}

export function validateInput(input: EditorInput): string[] {
  const errors: string[] = [];
  if (input.width_mm < 2000 || input.height_mm < 2000) errors.push("Размер комнаты должен быть не меньше 2000 мм.");
  if (input.width_mm > 12000 || input.height_mm > 12000) errors.push("MVP ограничен комнатой до 12000 мм по стороне.");
  if (input.collector_x_mm < 100 || input.collector_x_mm > input.width_mm - 100 || input.collector_y_mm < 100 || input.collector_y_mm > input.height_mm - 100) errors.push("Якорь маршрута коллектора должен быть внутри рабочей зоны.");
  if ([input.width_mm, input.height_mm, input.collector_x_mm, input.collector_y_mm].some((value) => value % 100 !== 0)) errors.push("Размеры и якорь маршрута должны лежать на сетке 100 мм.");
  input.exclusions.forEach((zone, index) => {
    if (zone.width_mm <= 0 || zone.height_mm <= 0) errors.push(`Препятствие ${index + 1}: размеры должны быть положительными.`);
    if (zone.x_mm < 0 || zone.y_mm < 0 || zone.x_mm + zone.width_mm > input.width_mm || zone.y_mm + zone.height_mm > input.height_mm) errors.push(`Препятствие ${index + 1} выходит за границу комнаты.`);
    if ([zone.x_mm, zone.y_mm, zone.width_mm, zone.height_mm].some((value) => value % 100 !== 0)) errors.push(`Препятствие ${index + 1}: координаты и размеры должны лежать на сетке 100 мм.`);
    input.exclusions.slice(index + 1).forEach((other, offset) => {
      const overlaps = zone.x_mm < other.x_mm + other.width_mm && zone.x_mm + zone.width_mm > other.x_mm && zone.y_mm < other.y_mm + other.height_mm && zone.y_mm + zone.height_mm > other.y_mm;
      if (overlaps) errors.push(`Препятствия ${index + 1} и ${index + offset + 2} перекрываются; MVP не суммирует такие площади.`);
    });
  });
  return errors;
}

export function serializeEditorProject(input: EditorInput): string {
  const project: EditorProjectFile = {
    schema_version: "1.0",
    kind: "homeaura-floor-heating-editor-input",
    units: "mm",
    input: {
      ...input,
      exclusions: [...input.exclusions].sort((first, second) => first.id.localeCompare(second.id)),
    },
  };
  return `${JSON.stringify(project, null, 2)}\n`;
}

export function parseEditorProject(value: string): EditorInput {
  const parsed = JSON.parse(value) as Partial<EditorProjectFile>;
  if (parsed.schema_version !== "1.0" || parsed.kind !== "homeaura-floor-heating-editor-input" || parsed.units !== "mm" || !parsed.input) {
    throw new Error("Файл не является проектом HomeAura Editor 1.0.");
  }
  const input = parsed.input as EditorInput;
  if (!supportedExteriorWalls.includes(input.exterior_wall)) throw new Error("Файл содержит неподдерживаемую наружную стену.");
  if (!Array.isArray(input.exclusions)) throw new Error("В файле отсутствует список препятствий.");
  const errors = validateInput(input);
  if (errors.length) throw new Error(errors[0]);
  return input;
}

function xmlEscape(value: string): string {
  return value.replaceAll("&", "&amp;").replaceAll('"', "&quot;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

export function serializeCoverageSvg(input: EditorInput, plan: CoveragePlan): string {
  const colors = ["#38bdf8", "#fb923c", "#a78bfa"];
  const routeMarkup = plan.circuit_routes.map((route, index) => {
    const points = route.polyline.map((point) => `${point.x_mm},${point.y_mm}`).join(" ");
    return `    <polyline id="${xmlEscape(route.id)}" data-length-mm="${route.length_mm}" points="${points}" fill="none" stroke="${colors[index % colors.length]}" stroke-width="20" stroke-linejoin="round"/>`;
  }).join("\n");
  const metadata = xmlEscape(JSON.stringify({
    units: "mm",
    plan_digest: plan.plan_digest,
    full_coverage_claimed: plan.full_coverage_claimed,
    route_ids: plan.circuit_routes.map((route) => route.id),
  }));
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${input.width_mm} ${input.height_mm}" data-units="mm">`,
    `  <metadata>${metadata}</metadata>`,
    `  <g id="ROOM_AND_ROUTES" transform="translate(0 ${input.height_mm}) scale(1 -1)">`,
    `    <rect id="ROOM_BOUNDARY" x="0" y="0" width="${input.width_mm}" height="${input.height_mm}" fill="#0b1920" stroke="#8ca1aa" stroke-width="14"/>`,
    routeMarkup,
    "  </g>",
    "</svg>",
    "",
  ].join("\n");
}

export function serializeCoverageReport(input: EditorInput, plan: CoveragePlan): string {
  return `${JSON.stringify({
    schema_version: "1.0",
    kind: "homeaura-floor-heating-coverage-report",
    units: "mm",
    input,
    plan,
  }, null, 2)}\n`;
}
