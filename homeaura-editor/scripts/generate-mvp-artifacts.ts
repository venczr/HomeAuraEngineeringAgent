import { createHash } from "node:crypto";
import { access, copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

import {
  buildCoverageRequest,
  type CoveragePlan,
  type EditorInput,
  serializeCoverageReport,
  serializeCoverageSvg,
  serializeEditorProject,
} from "../lib/floor-heating-contract.ts";

const generationId = "HA-EDITOR-MVP-20260813-B";
const editorRoot = resolve(import.meta.dirname, "..");
const artifactsRoot = resolve(editorRoot, "artifacts");
const outputRoot = resolve(artifactsRoot, generationId);
const editorUrl = process.env.HOMEAURA_EDITOR_URL ?? "http://127.0.0.1:3000";
const input: EditorInput = {
  width_mm: 7000,
  height_mm: 3200,
  collector_x_mm: 3500,
  collector_y_mm: 1100,
  exterior_wall: "SOUTH",
  exclusions: [],
};

try {
  await access(outputRoot);
  throw new Error(`Append-only output already exists: ${outputRoot}`);
} catch (error) {
  if (error instanceof Error && error.message.startsWith("Append-only")) throw error;
}

const response = await fetch(`${editorUrl}/api/floor-heating/coverage-preview`, {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify(buildCoverageRequest(input)),
});
if (!response.ok) throw new Error(`Coverage preview failed: ${response.status} ${await response.text()}`);
const plan = await response.json() as CoveragePlan;
if (plan.status === "impossible" || plan.circuit_routes.length === 0) throw new Error("Coverage plan is not exportable.");
if (plan.full_coverage_claimed) throw new Error("MVP must not claim full coverage.");
if (!plan.circuit_routes.every((route) => route.validation.valid)) throw new Error("An unvalidated route reached artifact generation.");

await mkdir(artifactsRoot, { recursive: true });
await mkdir(outputRoot, { recursive: false });
const files: Record<string, string | Uint8Array> = {
  "editor-project.json": serializeEditorProject(input),
  "canonical-coverage-plan.json": `${JSON.stringify(plan, null, 2)}\n`,
  "floor-heating-layout.svg": serializeCoverageSvg(input, plan),
  "floor-heating-report.json": serializeCoverageReport(input, plan),
};
for (const [name, value] of Object.entries(files)) await writeFile(resolve(outputRoot, name), value);

const screenshotSource = resolve(editorRoot, "homeaura-editor-mvp.png");
const screenshotTarget = resolve(outputRoot, "homeaura-editor-mvp.png");
await copyFile(screenshotSource, screenshotTarget);

const artifactNames = [...Object.keys(files), "homeaura-editor-mvp.png"];
const manifestEntries = [];
for (const name of artifactNames) {
  const bytes = await readFile(resolve(outputRoot, name));
  manifestEntries.push({
    name,
    bytes: bytes.length,
    sha256: createHash("sha256").update(bytes).digest("hex"),
  });
}
const manifest = {
  schema_version: "1.0",
  generation_id: generationId,
  units: "mm",
  fixture: input,
  plan_digest: plan.plan_digest,
  status: plan.status,
  full_coverage_claimed: plan.full_coverage_claimed,
  coverage_ratio: plan.coverage_ratio,
  routes: plan.circuit_routes.map((route) => ({ id: route.id, length_mm: route.length_mm, validation: route.validation.valid })),
  files: manifestEntries,
};
await writeFile(resolve(outputRoot, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
process.stdout.write(`${outputRoot}\n`);
