import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the HomeAura editor shell", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<title>HomeAura — редактор тёплого пола<\/title>/i);
  assert.match(html, /HomeAura/);
  assert.match(html, /Floor Heating Editor/);
  assert.match(html, /Рассчитать контуры/);
  assert.doesNotMatch(html, /Your site is taking shape|react-loading-skeleton/i);
});

test("editor preserves canonical geometry and honest MVP boundaries", async () => {
  const [editor, contract, proxy] = await Promise.all([
    readFile(new URL("../app/editor/HomeAuraEditor.tsx", import.meta.url), "utf8"),
    readFile(new URL("../lib/floor-heating-contract.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/api/floor-heating/coverage-preview/route.ts", import.meta.url), "utf8"),
  ]);

  assert.match(editor, /plan\?\.circuit_routes\.map/);
  assert.match(editor, /route\.polyline\.map/);
  assert.match(editor, /data-route-id=\{route\.id\}/);
  assert.match(editor, /requestNumber\.current \+= 1/);
  assert.match(editor, /setPlan\(null\)/);
  assert.match(editor, /scale\(1 -1\)/);
  assert.match(editor, /serializeEditorProject\(input\)/);
  assert.match(editor, /parseEditorProject\(await file\.text\(\)\)/);
  assert.match(editor, /serializeCoverageSvg\(input, plan\)/);
  assert.match(editor, /serializeCoverageReport\(input, plan\)/);
  assert.doesNotMatch(editor, /onClick=.*polyline|onPointer.*polyline/);
  assert.match(editor, /activeTool !== "ANCHOR"/);
  assert.match(editor, /Math\.round\(value \/ 100\) \* 100/);
  assert.match(editor, /onPointerDown=\{placeAnchor\}/);
  assert.match(editor, /ЧАСТИЧНОЕ ПОКРЫТИЕ/);
  assert.match(editor, /автоматический обход ещё не реализован/);
  assert.match(editor, /Не рассчитываются гидравлика/);
  assert.match(contract, /collector_point: point\(input\.collector_x_mm, input\.collector_y_mm\)/);
  assert.match(contract, /supportedExteriorWalls: WallSide\[\] = \["SOUTH", "NORTH"\]/);
  assert.match(contract, /должны лежать на сетке 100 мм/);
  assert.match(contract, /homeaura-floor-heating-editor-input/);
  assert.match(contract, /exclusions: \[\.\.\.input\.exclusions\]\.sort/);
  assert.match(proxy, /127\.0\.0\.1:8000/);
  assert.match(proxy, /HOMEAURA_API_BASE must remain loopback-only/);
  assert.match(proxy, /homeaura_api_unavailable/);
});
