import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=path.dirname(fileURLToPath(import.meta.url));
const hash=b=>createHash('sha256').update(b).digest('hex');
const planned=JSON.parse(readFileSync(path.join(root,'calls.json'),'utf8'));
assert.equal(planned.length,10);
const rows=[];
for(let n=1;n<=10;n++){
 const log=JSON.parse(readFileSync(path.join(root,`step-${n}.call.json`),'utf8'));
 assert.equal(log.stage,n);assert.equal(log.status,'success');assert.equal(log.attempt,1);
 assert.equal(log.prompt,planned[n-1].prompt);
 assert.equal(log.input,n===1?path.resolve(root,'../../assets/people/P01.png'):path.join(root,`step-${n-1}.png`));
 const output=readFileSync(log.output);const input=readFileSync(log.input);
 assert.equal(hash(output),hash(readFileSync(log.source)));
 assert.equal(output.subarray(1,4).toString(),'PNG');
 assert.equal(hash(output),hash(readFileSync(path.resolve(root,`../../evaluation/public/ten-stage/step-${n}.png`))));
 rows.push({stage:n,input_sha256:hash(input),output_sha256:hash(output),width:output.readUInt32BE(16),height:output.readUInt32BE(20)});
}
console.log(JSON.stringify({experiment:'ten-stage-v1',person:'P01',runs:1,verified:true,images:rows},null,2));
