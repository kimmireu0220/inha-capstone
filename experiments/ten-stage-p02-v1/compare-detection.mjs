import {readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const read=p=>JSON.parse(readFileSync(path.join(root,p)));
const mapping=read('metrics/blind-mapping.json').presentation_order;
const ratings=read('agent-review/blind-review.json').ratings.map(r=>({...r,step:mapping.find(m=>m.file===r.id+'.png').step})).sort((a,b)=>a.step-b.step);
const detection=read('detection.json');
const compare=excludeUncertain=>detection.detectors.map(d=>{
 let tp=0,tn=0,fp=0,fn=0;
 const included=ratings.filter(r=>!excludeUncertain||!r.uncertain);
 for(const r of included){const alarm=d.predictions.find(p=>p.step===r.step).alarm;const positive=r.naturalness>=2;if(positive){if(alarm)tp++;else fn++;}else{if(alarm)fp++;else tn++;}}
 return {metric:d.metric,first_alarm:d.first_alarm,compared_steps:included.map(r=>r.step),tp,tn,fp,fn};
});
console.log(JSON.stringify({ratings,first_agent_positive:ratings.find(r=>r.naturalness>=2)?.step??null,first_certain_positive:ratings.find(r=>r.naturalness>=2&&!r.uncertain)?.step??null,including_uncertain:compare(false),excluding_uncertain:compare(true),limitations:'Agent-relative agreement on ten dependent stages, one portrait. Not human-ground-truth accuracy. Only one clearly negative stage, and stage 2 is uncertain.'},null,2));
