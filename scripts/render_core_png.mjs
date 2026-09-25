import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
const require=createRequire(import.meta.url); const {Resvg}=require('./../.tmp_svg_rasterizer/node_modules/@resvg/resvg-js');
const svg=readFileSync(process.argv[2],'utf8'); const png=new Resvg(svg,{fitTo:{mode:'width',value:1400}}).render().asPng(); writeFileSync(process.argv[3],png);
