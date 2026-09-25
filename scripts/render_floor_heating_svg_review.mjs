import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { deflateSync } from "node:zlib";


function fail(message) {
  throw new Error(message);
}


function argument(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || index + 1 >= process.argv.length) fail(`missing ${name}`);
  return resolve(process.argv[index + 1]);
}


const sourcePath = argument("--source");
const outputDirectory = argument("--output");
const moduleRoot = argument("--module-root");
if (!existsSync(sourcePath)) fail(`source SVG missing: ${sourcePath}`);
if (!existsSync(outputDirectory)) mkdirSync(outputDirectory, { recursive: true });

const require = createRequire(import.meta.url);
const { Resvg } = require(resolve(moduleRoot, "node_modules", "@resvg", "resvg-js"));
const source = readFileSync(sourcePath, "utf8");
const sourceHash = createHash("sha256").update(Buffer.from(source, "utf8")).digest("hex");
const scriptHash = createHash("sha256").update(readFileSync(new URL(import.meta.url))).digest("hex");
const expectedHash = "cce0a1d361ba7135d77c53dea3cae402475a7ecba73f3e0a5d2f3230c2452d18";
if (sourceHash !== expectedHash) fail("BLOCKED_VISUAL_ARTIFACT_IDENTITY_MISMATCH");


function engineeringViewBox(viewBox) {
  const values = viewBox.trim().split(/\s+/).map(Number);
  if (values.length !== 4 || values.some((value) => !Number.isFinite(value))) {
    fail(`invalid viewBox ${viewBox}`);
  }
  return values;
}


function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}


function pngChunk(type, data) {
  const typeBytes = Buffer.from(type, "ascii");
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length);
  const checksum = Buffer.alloc(4);
  checksum.writeUInt32BE(crc32(Buffer.concat([typeBytes, data])));
  return Buffer.concat([length, typeBytes, data, checksum]);
}


function encodeRgbaPng(width, height, rgba) {
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header[8] = 8;
  header[9] = 6;
  const scanlines = Buffer.alloc(height * (1 + width * 4));
  for (let y = 0; y < height; y += 1) {
    const target = y * (1 + width * 4);
    scanlines[target] = 0;
    rgba.copy(scanlines, target + 1, y * width * 4, (y + 1) * width * 4);
  }
  return Buffer.concat([
    Buffer.from("89504e470d0a1a0a", "hex"),
    pngChunk("IHDR", header),
    pngChunk("IDAT", deflateSync(scanlines, { level: 9 })),
    pngChunk("IEND", Buffer.alloc(0)),
  ]);
}


function cropEngineeringPixels(rendered, viewBox, desiredWidth) {
  const sourceViewBox = [-700, -500, 11700, 4200];
  const [x, y, width, height] = engineeringViewBox(viewBox);
  const scale = rendered.width / sourceViewBox[2];
  const verticalOffset = (rendered.height - sourceViewBox[3] * scale) / 2;
  const left = Math.round((x - sourceViewBox[0]) * scale);
  const top = Math.round(verticalOffset + (y - sourceViewBox[1]) * scale);
  const cropWidth = Math.round(width * scale);
  const cropHeight = Math.round(height * scale);
  if (Math.abs(cropWidth - desiredWidth) > 1) fail("unexpected raster crop scale");
  if (left < 0 || top < 0 || left + cropWidth > rendered.width || top + cropHeight > rendered.height) {
    fail(`raster crop outside source: ${viewBox}`);
  }
  const sourcePixels = rendered.pixels;
  const cropped = Buffer.alloc(cropWidth * cropHeight * 4);
  for (let row = 0; row < cropHeight; row += 1) {
    const sourceStart = ((top + row) * rendered.width + left) * 4;
    sourcePixels.copy(
      cropped,
      row * cropWidth * 4,
      sourceStart,
      sourceStart + cropWidth * 4,
    );
  }
  return { png: encodeRgbaPng(cropWidth, cropHeight, cropped), width: cropWidth, height: cropHeight };
}


function hidden(svg, ids) {
  let result = svg;
  for (const id of ids) {
    const token = `<g id="${id}"`;
    if (!result.includes(token)) fail(`missing SVG layer ${id}`);
    result = result.replace(token, `<g id="${id}" style="display:none"`);
  }
  return result;
}


const variants = [
  { name: "full-layout.png", viewBox: "-700 -500 11700 4200", width: 2200, hidden: [] },
  { name: "room-close-up.png", viewBox: "-500 -450 8000 4100", width: 2200, hidden: ["DIAGNOSTICS"] },
  {
    name: "collector-close-up.png", viewBox: "900 2425 6100 850", width: 2400,
    hidden: [
      "DIAGNOSTICS", "ROOM_DIMENSIONS", "PERIMETER_ZONE", "FIELD_ZONE",
      "EXCLUSION_ZONES", "UNCOVERED_AREA_OVERLAY",
    ],
  },
  {
    name: "central-turn-close-up.png", viewBox: "1050 2600 4900 600", width: 2400,
    hidden: [
      "DIAGNOSTICS", "ROOM_DIMENSIONS", "PERIMETER_ZONE", "FIELD_ZONE",
      "EXCLUSION_ZONES", "COLLECTOR", "FLOW_DIRECTION", "UNCOVERED_AREA_OVERLAY",
    ],
  },
  {
    name: "pipes-only.png", viewBox: "-500 -350 8000 3900", width: 2200,
    hidden: [
      "REFERENCE_GRID", "ROOM_DIMENSIONS", "PERIMETER_ZONE", "FIELD_ZONE",
      "EXCLUSION_ZONES", "FLOW_DIRECTION", "DIAGNOSTICS", "UNCOVERED_AREA_OVERLAY",
    ],
  },
  {
    name: "engineering-debug.png", viewBox: "500 1850 6000 1400", width: 2400,
    hidden: ["DIAGNOSTICS", "ROOM_DIMENSIONS"],
  },
];

const captures = [];
for (const variant of variants) {
  const outputPath = resolve(outputDirectory, variant.name);
  if (existsSync(outputPath)) fail(`refusing to overwrite ${outputPath}`);
  const derivedSvg = hidden(source, variant.hidden);
  const targetViewBox = engineeringViewBox(variant.viewBox);
  const renderWidth = Math.ceil(variant.width * 11700 / targetViewBox[2]);
  const renderer = new Resvg(derivedSvg, {
    background: "white",
    fitTo: { mode: "width", value: renderWidth },
    shapeRendering: 2,
    textRendering: 1,
    imageRendering: 0,
    font: { loadSystemFonts: true, defaultFontFamily: "Arial" },
  });
  const rendered = renderer.render();
  const cropped = cropEngineeringPixels(rendered, variant.viewBox, variant.width);
  const png = cropped.png;
  writeFileSync(outputPath, png, { flag: "wx" });
  captures.push({
    name: variant.name,
    source_svg_sha256: sourceHash,
    derived_viewbox: variant.viewBox,
    hidden_layer_ids: variant.hidden,
    output_width_px: cropped.width,
    output_height_px: cropped.height,
    png_sha256: createHash("sha256").update(png).digest("hex"),
    pipe_coordinate_modification: false,
  });
}

const provenancePath = resolve(outputDirectory, "capture_provenance.json");
if (existsSync(provenancePath)) fail(`refusing to overwrite ${provenancePath}`);
writeFileSync(
  provenancePath,
  `${JSON.stringify({
    capture_version: "HA-FH-VIS-002/1.1",
    renderer: "@resvg/resvg-js@2.6.2",
    capture_script_sha256: scriptHash,
    raster_crop_method: "post-render RGBA pixel crop from declared engineering viewBox",
    png_encoder: "PNG RGBA8 filter-none; node:zlib level=9; CRC32 per PNG chunk",
    canonical_coordinate_modification: false,
    source_svg_path: sourcePath,
    source_svg_sha256: sourceHash,
    captures,
  }, null, 2)}\n`,
  { encoding: "utf8", flag: "wx" },
);

process.stdout.write(`${JSON.stringify({ source_svg_sha256: sourceHash, captures }, null, 2)}\n`);
