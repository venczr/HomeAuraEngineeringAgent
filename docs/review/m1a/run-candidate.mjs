import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const repo=path.resolve(process.argv[2]);
const out=path.resolve(process.argv[3]);
const require=createRequire(path.join(repo,'package.json'));
const ts=require('typescript');
const fixture=JSON.parse(fs.readFileSync(path.join(out,'fixture.json'),'utf8'));
const fixtureHash=createHash('sha256').update(fs.readFileSync(path.join(out,'fixture.json'))).digest('hex');
const compiled=path.join(repo,'.m1a');fs.mkdirSync(compiled,{recursive:true});
for(const name of ['pipeSpec','geometry/spiral']){
  let code=ts.transpileModule(fs.readFileSync(path.join(repo,'src',name+'.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.ES2022,target:ts.ScriptTarget.ES2022}}).outputText;
  code=code.replaceAll("'../pipeSpec'","'./pipeSpec.mjs'");
  fs.writeFileSync(path.join(compiled,path.basename(name)+'.mjs'),code);
}
const {generateSpiral}=await import(pathToFileURL(path.join(compiled,'spiral.mjs')));
const args=[{points:fixture.polygon.map(([x,y])=>({x,y}))},fixture.pitch_mm,{x:fixture.connection_hint[0],y:fixture.connection_hint[1]},fixture.padding_mm,false];
const start=performance.now();const points=generateSpiral(...args);const elapsed=performance.now()-start;
const repeat=generateSpiral(...args);
fs.writeFileSync(path.join(out,'candidate.json'),JSON.stringify({commit:'bafc690f340943f6e04f9bf9a34b2c1e268d39e0',fixture_sha256:fixtureHash,elapsed_ms:elapsed,repeat_identical:JSON.stringify(points)===JSON.stringify(repeat),points},null,2));
console.log(JSON.stringify({point_count:points.length,elapsed_ms:elapsed,repeat_identical:JSON.stringify(points)===JSON.stringify(repeat),fixture_sha256:fixtureHash}));
