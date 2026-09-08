import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=path.dirname(fileURLToPath(import.meta.url));
const rows=JSON.parse(readFileSync(path.join(root,'metrics/metrics.json'))).results;
const definitions=[['mae_0_1',0.0288375,'gte'],['ssim',0.842874,'lte'],['lpips_alex_v0_1',0.0555075,'gte']];
const detectors=definitions.map(([metric,threshold,direction])=>{
 const predictions=rows.map(r=>({step:r.step,value:r[metric],alarm:direction==='gte'?r[metric]>=threshold:r[metric]<=threshold}));
 return {metric,threshold,direction,first_alarm:predictions.find(p=>p.alarm)?.step??null,predictions};
});
console.log(JSON.stringify({primary:'lpips_alex_v0_1',threshold_source:'P01 stage2/stage3 midpoint, rounded and fixed in PROTOCOL.md before P02 generation',online_execution:false,note:'Offline replay of fixed rules; not human-validated detector accuracy.',detectors},null,2));
