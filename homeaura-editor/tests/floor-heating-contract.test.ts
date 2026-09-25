import assert from "node:assert/strict";
import test from "node:test";

import {
  buildCoverageRequest,
  type EditorInput,
  parseEditorProject,
  serializeCoverageReport,
  serializeCoverageSvg,
  serializeEditorProject,
} from "../lib/floor-heating-contract.ts";

const input: EditorInput = {
  width_mm: 7000,
  height_mm: 3200,
  collector_x_mm: 3500,
  collector_y_mm: 1100,
  exterior_wall: "SOUTH",
  exclusions: [
    { id: "zone-b", x_mm: 2000, y_mm: 1200, width_mm: 200, height_mm: 200 },
    { id: "zone-a", x_mm: 1000, y_mm: 1200, width_mm: 200, height_mm: 200 },
  ],
};

test("project file is byte-stable and contains only editor input", () => {
  const first = serializeEditorProject(input);
  const second = serializeEditorProject({ ...input, exclusions: [...input.exclusions].reverse() });
  assert.equal(first, second);
  assert.match(first, /homeaura-floor-heating-editor-input/);
  assert.ok(first.indexOf("zone-a") < first.indexOf("zone-b"));
  assert.doesNotMatch(first, /circuit_routes|polyline|plan_digest/);
});

test("valid project round-trips and still requires an engine request", () => {
  const restored = parseEditorProject(serializeEditorProject(input));
  assert.deepEqual(restored.exclusions.map((zone) => zone.id), ["zone-a", "zone-b"]);
  const request = buildCoverageRequest(restored);
  assert.equal(request.collector_point.x_mm, 3500);
  assert.equal(request.exterior_wall_segments[0].reference, "exterior-south");
});

test("foreign and invalid project files fail closed", () => {
  assert.throws(() => parseEditorProject('{"kind":"other"}'), /не является проектом/);
  const invalid = JSON.parse(serializeEditorProject(input));
  invalid.input.width_mm = 7050;
  assert.throws(() => parseEditorProject(JSON.stringify(invalid)), /сетке 100 мм/);
});

test("coverage exports preserve exact canonical route order", () => {
  const plan = {
    status: "partial" as const,
    required_circuit_count: 1,
    collector_port_count: 1,
    heated_area_mm2: 22400000,
    estimated_coverage_mm2: 10000000,
    coverage_ratio: 0.4,
    full_coverage_claimed: false,
    zones: [{ zone_id: "zone-1", route_anchor_point: { x_mm: 3500, y_mm: 1100 } }],
    circuit_routes: [{
      id: "route-1",
      polyline: [{ x_mm: 100, y_mm: 100 }, { x_mm: 200, y_mm: 100 }, { x_mm: 200, y_mm: 300 }],
      length_mm: 300,
      collector_supply_point: { x_mm: 100, y_mm: 100 },
      collector_return_point: { x_mm: 200, y_mm: 300 },
      validation: { connected: true, self_intersection: false, branches: false, step_valid: true, length_valid: true, inside_boundary: true, exclusion_clear: true, endpoints_valid: true, valid: true },
    }],
    diagnostics: ["COVERAGE_ESTIMATE_ONLY_FULL_COVERAGE_NOT_CLAIMED"],
    plan_digest: "a".repeat(64),
  };
  const svg = serializeCoverageSvg(input, plan);
  assert.match(svg, /points="100,100 200,100 200,300"/);
  assert.match(svg, /full_coverage_claimed&quot;:false/);
  assert.equal((svg.match(/<polyline/g) ?? []).length, 1);
  const report = serializeCoverageReport(input, plan);
  assert.deepEqual(JSON.parse(report).plan.circuit_routes[0].polyline, plan.circuit_routes[0].polyline);
});
