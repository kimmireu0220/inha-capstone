import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=path.dirname(fileURLToPath(import.meta.url));
const read=p=>JSON.parse(readFileSync(path.resolve(root,p)));
const human=read('response-01.json');
const detection=read('../detection.json');
const rows=human.ratings;
const detectors=detection.detectors.map(d=>{
 let tp=0,tn=0,fp=0,fn=0;
 for(const r of rows){if(r.score===null)continue;const p=d.predictions.find(x=>x.step===r.step).alarm; if(r.score>=2){if(p)tp++;else fn++;}else{if(p)fp++;else tn++;}}
 return {metric:d.metric,threshold:d.threshold,first_alarm:d.first_alarm,tp,tn,fp,fn};
});
const mapping=read('../metrics/blind-mapping.json').presentation_order;
const agent=read('../agent-review/blind-review.json').ratings;
const ordinal=rows.map(h=>{const a=agent.find(r=>r.id+'.png'===mapping.find(m=>m.step===h.step).file);return {step:h.step,human:h.score,agent:a.naturalness,agent_uncertain:a.uncertain,exact_agreement:h.score===a.naturalness};});
console.log(JSON.stringify({human_first_clear_or_severe_step:rows.find(r=>r.score>=2)?.step??null,positive_definition:'score >= 2 (clear or severe), not any change',detectors,agent_comparison:ordinal,limitations:'One response set on ten dependent images. No universal accuracy claim. Thresholds unchanged. Evaluator identity/prior exposure unconfirmed.'},null,2));
