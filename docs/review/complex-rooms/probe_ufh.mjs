import fs from 'node:fs';import path from 'node:path';import{createRequire}from'node:module';import{pathToFileURL}from'node:url';
const repo=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);
const require=createRequire(path.join(repo,'package.json')),ts=require('typescript');
const inserts=JSON.parse(fs.readFileSync(path.join(out,'../m1a-v2/trace-instrumentation.json'),'utf8')).insertions;
let src=fs.readFileSync(path.join(repo,'src/geometry/spiral.ts'),'utf8');
for(const [a,b]of inserts){if(src.split(a).length!==2)throw Error('Unexpected source');src=src.replace(a,b);}
const build=path.join(repo,'.complex-probe');fs.mkdirSync(build,{recursive:true});
for(const[name,source]of[['spiral',src],['pipeSpec',fs.readFileSync(path.join(repo,'src/pipeSpec.ts'),'utf8')]]){
 const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ES2022,target:ts.ScriptTarget.ES2022}}).outputText.replaceAll("'../pipeSpec'","'./pipeSpec.mjs'");fs.writeFileSync(path.join(build,name+'.mjs'),code);
}
const {generateSpiral}=await import(pathToFileURL(path.join(build,'spiral.mjs')));
const outline=JSON.parse(fs.readFileSync(path.join(out,'fixtures.json'),'utf8')).L_room.outline;
globalThis.__arcs=[];
const points=generateSpiral({points:outline.map(([x,y])=>({x,y}))},200,{x:0,y:0},100,false);
const traces=globalThis.__arcs.map(t=>{const c=globalThis.__map({x:t.cx,y:t.cy}),pts=t.pts.map(globalThis.__map);return{c:[c.x,c.y],r:t.r,start:Math.atan2(pts[0].y-c.y,pts[0].x-c.x),sweep:t.endAngle-t.startAngle,pts};});
const options=traces.flatMap(t=>[t,{...t,start:t.start+t.sweep,sweep:-t.sweep,pts:[...t.pts].reverse()}]);
const equal=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y)<1e-6;
let curves=[],i=0;
while(i<points.length-1){const t=options.find(t=>i+t.pts.length<=points.length&&t.pts.every((p,k)=>equal(p,points[i+k])));
 if(t){curves.push({kind:'arc',c:t.c,r:t.r,start:t.start,sweep:t.sweep});i+=t.pts.length-1;}
 else{curves.push({kind:'line',a:[points[i].x,points[i].y],b:[points[i+1].x,points[i+1].y]});i++;}}
fs.writeFileSync(path.join(out,'L-ufh-candidate.json'),JSON.stringify({points,curves,outline,export_allowed:false,scope:'Raw one-circuit L probe; endpoint hint is not an exact terminal contract'},null,2));
console.log(JSON.stringify({points:points.length,arcs:curves.filter(c=>c.kind==='arc').length}));
