import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { deflateSync } from "node:zlib";


function fail(message) { throw new Error(message); }
function argument(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || index + 1 >= process.argv.length) fail(`missing ${name}`);
  return process.argv[index + 1];
}


const sourcePath = resolve(argument("--source"));
const outputDirectory = resolve(argument("--output"));
const moduleRoot = resolve(argument("--module-root"));
const expectedHash = argument("--expected-sha").toLowerCase();
if (!existsSync(sourcePath)) fail(`source SVG missing: ${sourcePath}`);
if (!existsSync(outputDirectory)) mkdirSync(outputDirectory, { recursive: true });
const require = createRequire(import.meta.url);
const { Resvg } = require(resolve(moduleRoot, "node_modules", "@resvg", "resvg-js"));
const source = readFileSync(sourcePath, "utf8");
const sourceHash = createHash("sha256").update(Buffer.from(source, "utf8")).digest("hex");
const scriptHash = createHash("sha256").update(readFileSync(new URL(import.meta.url))).digest("hex");
if (sourceHash !== expectedHash) fail("VIS003_SVG_IDENTITY_MISMATCH");


function hidden(svg, ids) {
  let result = svg;
  for (const id of ids) {
    const token = `<g id="${id}"`;
    if (!result.includes(token)) fail(`missing SVG layer ${id}`);
    result = result.replace(token, `<g id="${id}" style="display:none"`);
  }
  return result;
}


function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
  }
  return (crc ^ 0xffffffff) >>> 0;
}


function chunk(type, data) {
  const name = Buffer.from(type, "ascii");
  const length = Buffer.alloc(4); length.writeUInt32BE(data.length);
  const checksum = Buffer.alloc(4); checksum.writeUInt32BE(crc32(Buffer.concat([name, data])));
  return Buffer.concat([length, name, data, checksum]);
}


function encode(width, height, rgba) {
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0); header.writeUInt32BE(height, 4); header[8] = 8; header[9] = 6;
  const scanlines = Buffer.alloc(height * (1 + width * 4));
  for (let y = 0; y < height; y += 1) {
    const target = y * (1 + width * 4); scanlines[target] = 0;
    rgba.copy(scanlines, target + 1, y * width * 4, (y + 1) * width * 4);
  }
  return Buffer.concat([
    Buffer.from("89504e470d0a1a0a", "hex"), chunk("IHDR", header),
    chunk("IDAT", deflateSync(scanlines, { level: 9 })), chunk("IEND", Buffer.alloc(0)),
  ]);
}


const sourceViewBox = [-600, -650, 10400, 4450];
function crop(rendered, viewBox, desiredWidth) {
  const [x, y, width, height] = viewBox.trim().split(/\s+/).map(Number);
  const scale = rendered.width / sourceViewBox[2];
  const renderedContentHeight = sourceViewBox[3] * scale;
  const verticalOffset = (rendered.height - renderedContentHeight) / 2;
  const left = Math.round((x - sourceViewBox[0]) * scale);
  const top = Math.round(verticalOffset + (y - sourceViewBox[1]) * scale);
  const cropWidth = Math.round(width * scale);
  const cropHeight = Math.round(height * scale);
  if (Math.abs(cropWidth - desiredWidth) > 1 || left < 0 || top < 0 || left + cropWidth > rendered.width || top + cropHeight > rendered.height) fail(`invalid crop ${viewBox}`);
  const pixels = Buffer.alloc(cropWidth * cropHeight * 4);
  const sourcePixels = rendered.pixels;
  for (let row = 0; row < cropHeight; row += 1) {
    const start = ((top + row) * rendered.width + left) * 4;
    sourcePixels.copy(pixels, row * cropWidth * 4, start, start + cropWidth * 4);
  }
  return { png: encode(cropWidth, cropHeight, pixels), width: cropWidth, height: cropHeight };
}


const variants = [
  { name: "full-layout.png", viewBox: "-600 -650 10400 4450", width: 2400, hidden: [] },
  { name: "pipes-only.png", viewBox: "-150 -500 7300 3900", width: 2300, hidden: ["GRID", "WALL_CLASSIFICATIONS", "EXTERIOR_WALL_THREE_PASS_REGION", "CIRCUIT_TERRITORIES", "COVERAGE", "FLOW_ARROWS", "CENTRE_TURN_CLASSIFICATIONS", "ANNOTATIONS", "DIAGNOSTICS"] },
  { name: "collector-transits-close-up.png", viewBox: "1000 -500 5200 650", width: 2400, hidden: ["GRID", "CIRCUIT_TERRITORIES", "COVERAGE", "ANNOTATIONS", "DIAGNOSTICS"] },
  { name: "circuit-1-close-up.png", viewBox: "-100 -100 3700 3400", width: 1900, hidden: ["CIRCUIT_2", "COVERAGE", "DIAGNOSTICS"] },
  { name: "circuit-2-close-up.png", viewBox: "3400 -100 3700 3400", width: 1900, hidden: ["CIRCUIT_1", "COVERAGE", "DIAGNOSTICS"] },
  { name: "exterior-wall-three-pass-close-up.png", viewBox: "-100 2700 7200 600", width: 2400, hidden: ["DIAGNOSTICS", "COLLECTOR"] },
  { name: "centre-turn-c1.png", viewBox: "850 1750 2100 950", width: 1900, hidden: ["CIRCUIT_2", "COLLECTOR", "SUPPLY_TRANSITS", "RETURN_TRANSITS", "DIAGNOSTICS", "COVERAGE"] },
  { name: "centre-turn-c2.png", viewBox: "4350 1750 2100 950", width: 1900, hidden: ["CIRCUIT_1", "COLLECTOR", "SUPPLY_TRANSITS", "RETURN_TRANSITS", "DIAGNOSTICS", "COVERAGE"] },
  { name: "coverage-diagnostic.png", viewBox: "-100 -100 7200 3400", width: 2300, hidden: ["COLLECTOR", "SUPPLY_TRANSITS", "RETURN_TRANSITS", "FLOW_ARROWS", "DIAGNOSTICS"] },
];


const captures = [];
for (const variant of variants) {
  const outputPath = resolve(outputDirectory, variant.name);
  if (existsSync(outputPath)) fail(`refusing to overwrite ${outputPath}`);
  const targetWidth = Number(variant.viewBox.split(/\s+/)[2]);
  const renderWidth = Math.ceil(variant.width * sourceViewBox[2] / targetWidth);
  const renderer = new Resvg(hidden(source, variant.hidden), {
    background: "white", fitTo: { mode: "width", value: renderWidth },
    shapeRendering: 2, textRendering: 1, imageRendering: 0,
    font: { loadSystemFonts: true, defaultFontFamily: "Arial" },
  });
  const rendered = renderer.render();
  const value = crop(rendered, variant.viewBox, variant.width);
  writeFileSync(outputPath, value.png, { flag: "wx" });
  captures.push({
    name: variant.name, source_svg_sha256: sourceHash, display_viewbox: variant.viewBox,
    hidden_layer_ids: variant.hidden, output_width_px: value.width, output_height_px: value.height,
    png_sha256: createHash("sha256").update(value.png).digest("hex"),
    canonical_coordinate_modification: false,
  });
}


const provenancePath = resolve(outputDirectory, "capture_provenance.json");
writeFileSync(provenancePath, `${JSON.stringify({
  capture_version: "HA-FH-VIS-003/1.0", renderer: "@resvg/resvg-js@2.6.2",
  capture_script_sha256: scriptHash, raster_crop_method: "post-render RGBA pixel crop from declared display viewBox",
  png_encoder: "PNG RGBA8 filter-none; node:zlib level=9; CRC32 per PNG chunk",
  source_svg_path: sourcePath, source_svg_sha256: sourceHash,
  canonical_coordinate_modification: false, captures,
}, null, 2)}\n`, { encoding: "utf8", flag: "wx" });
process.stdout.write(`${JSON.stringify({ source_svg_sha256: sourceHash, captures }, null, 2)}\n`);
