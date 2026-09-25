// Experimental trace sidecar + bounded terminal adapter. No upstream source edits.
import fs from 'node:fs';import path from 'node:path';import {createRequire} from 'node:module';import {pathToFileURL} from 'node:url';import {createHash} from 'node:crypto';
const repo=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);
const require=createRequire(path.join(repo,'package.json')),ts=require('typescript');
const compiled=path.join(repo,'.m1a-v2');fs.mkdirSync(compiled,{recursive:true});
const original=fs.readFileSync(path.join(repo,'src/geometry/spiral.ts'),'utf8');
const inserts=[['    return pts;','    globalThis.__arcs.push({cx,cy,r,startAngle,endAngle,pts});\n    return pts;'],['    return canonicalPath.map(point => {','    globalThis.__map = point => transformFromCanonical(mirror ? {x:canonicalWidth-point.x,y:point.y} : point, side,xMin,xMax,yMin,yMax);\n    return canonicalPath.map(point => {']];
let instrumented=original;
for(const [find,replacement] of inserts){if(instrumented.split(find).length!==2)throw Error('Trace anchor no longer unique');instrumented=instrumented.replace(find,replacement);}
fs.writeFileSync(path.join(out,'trace-instrumentation.json'),JSON.stringify({source_sha256:createHash('sha256').update(original).digest('hex'),insertions:inserts},null,2));
for(const [name,src] of [['spiral',instrumented],['pipeSpec',fs.readFileSync(path.join(repo,'src/pipeSpec.ts'),'utf8')]]){
  const js=ts.transpileModule(src,{compilerOptions:{module:ts.ModuleKind.ES2022,target:ts.ScriptTarget.ES2022}}).outputText.replaceAll("'../pipeSpec'","'./pipeSpec.mjs'");fs.writeFileSync(path.join(compiled,name+'.mjs'),js);
}
const {generateSpiral}=await import(pathToFileURL(path.join(compiled,'spiral.mjs')));
const same=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y)<1e-6;
function extract(height){
  globalThis.__arcs=[];
  const points=generateSpiral({points:[{x:0,y:0},{x:4000,y:0},{x:4000,y:height},{x:0,y:height}]},200,{x:0,y:0},100,false);
  const traces=globalThis.__arcs.map(t=>{const c=globalThis.__map({x:t.cx,y:t.cy}),pts=t.pts.map(globalThis.__map);return {c:[c.x,c.y],r:t.r,start:Math.atan2(pts[0].y-c.y,pts[0].x-c.x),sweep:t.endAngle-t.startAngle,pts};});
  const alternatives=traces.flatMap(t=>[t,{...t,start:t.start+t.sweep,sweep:-t.sweep,pts:[...t.pts].reverse()}]);
  let i=0,curves=[],matched=0;
  while(i<points.length-1){
    const t=alternatives.find(t=>t.pts.length>=3&&i+t.pts.length<=points.length&&t.pts.every((p,k)=>same(p,points[i+k])));
    if(t){curves.push({kind:'arc',c:t.c,r:t.r,start:t.start,sweep:t.sweep});i+=t.pts.length-1;matched++;}
    else{curves.push({kind:'line',a:[points[i].x,points[i].y],b:[points[i+1].x,points[i+1].y]});i++;}
  }
  return {points,curves,matched_arc_count:matched,generated_arc_trace_count:traces.length};
}
const raw=extract(3000),old=JSON.parse(fs.readFileSync(path.join(out,'../m1a/candidate.json'),'utf8'));
if(JSON.stringify(raw.points)!==JSON.stringify(old.points))throw Error('Instrumentation changed original candidate');
fs.writeFileSync(path.join(out,'ufh-analytic-original.json'),JSON.stringify(raw,null,2));
const source=extract(2800);
let core=source.curves.map(p=>p.kind==='line'?{...p,a:p.a.map(x=>x+100),b:p.b.map(x=>x+100)}:{...p,c:p.c.map(x=>x+100)});
const first=core[0],last=core.at(-1);
if(first.kind!=='line'||last.kind!=='line'||Math.hypot(first.a[0]-3900,first.a[1]-200)>1e-6||Math.hypot(last.b[0]-3700,last.b[1]-200)>1e-6||last.a[1]<=400)throw Error('Unsupported upstream terminal geometry');
last.b=[3700,400];
const line=(a,b)=>({kind:'line',a,b}),arc=(c,start,sweep)=>({kind:'arc',c,r:100,start,sweep});
const curves=[line([200,100],[3800,100]),arc([3800,200],-Math.PI/2,Math.PI/2),...core,
  arc([3600,400],0,-Math.PI/2),line([3600,300],[200,300]),arc([200,400],-Math.PI/2,-Math.PI/2),
  line([100,400],[100,2800]),arc([200,2800],Math.PI,-Math.PI/2),line([200,2900],[3800,2900])];
fs.writeFileSync(path.join(out,'ufh-adapted.json'),JSON.stringify({curves,core_source:source,placement_translation:[100,100],virtual_generator_rectangle:[4000,2800],fixed_fixture_sha256:createHash('sha256').update(fs.readFileSync(path.join(out,'fixture.json'))).digest('hex'),note:'Virtual construction frame is not allowed physical floor. Final physical curves independently checked. Preserves upstream interior; trims final return line and adds explicit terminal arcs/lines.'},null,2));
console.log(JSON.stringify({raw_arcs:raw.matched_arc_count,adapted_core_arcs:source.matched_arc_count,adapted_primitives:curves.length,original_points_unchanged:true}));
