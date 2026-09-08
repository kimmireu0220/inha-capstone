'use client';
// Hydrate browser-only saved responses after SSR; timestamps are created only in click handlers.
/* eslint-disable react/react-compiler */
// Scientific comparison images must retain their original pixels without image optimization.
/* eslint-disable next/no-img-element */
import {useEffect,useRef,useState} from 'react';
import {Button} from '@/components/ui/button';
import candidates from './data.json';
import '../review.css';

const modes=['face','requirements'] as const;
type Mode=typeof modes[number];
type Answer={value:string;updatedAt:string};
const schemas:Record<Mode,string>={face:'current-final-human-v1',requirements:'current-final-human-v2'};
const labels={face:'얼굴 변화',requirements:'인물 얼굴 보존'};
const grades=[['0','없음'],['1','약함'],['2','뚜렷함'],['3','심함'],['unknown','판단 어려움']];
const preserved=[['2','유지'],['1','일부 유지'],['0','미유지'],['unknown','판단 어려움']];
function makeTasks(mode:Mode){return candidates.map(c=>{const [kind,title]=mode==='face'?['face','원본에 없던 부자연스러운 피부 무늬나 얼굴 변형이 보이나요?']:['face_preservation','바꾸라고 하지 않은 얼굴이 원본과 동일하게 보존됐나요?'];return{id:c.id+'-'+kind,candidate:c,kind,title,options:mode==='requirements'?preserved:grades};});}
export default function CurrentReview(){
 const [mode,setMode]=useState<Mode>('face'),[ready,setReady]=useState(false),[index,setIndex]=useState(0),[answers,setAnswers]=useState<Record<string,Answer>>({}),[rater,setRater]=useState('R01'),[error,setError]=useState(''),[saved,setSaved]=useState(false);
 const lock=useRef(false),timer=useRef<ReturnType<typeof setTimeout>|null>(null);
 const tasks=makeTasks(mode),item=tasks[index],schema=schemas[mode],key=schema+'-'+mode;
 useEffect(()=>{const q=new URLSearchParams(location.search).get('part');const selected=modes.includes(q as Mode)?q as Mode:'face';const selectedSchema=schemas[selected];setMode(selected);const list=makeTasks(selected);try{const raw=localStorage.getItem(selectedSchema+'-'+selected);if(raw){const d=JSON.parse(raw);if(d.schema===selectedSchema&&d.mode===selected){const valid:Record<string,Answer>={};for(const t of list){const a=d.answers?.[t.id];if(a&&t.options.some(o=>o[0]===a.value)&&typeof a.updatedAt==='string')valid[t.id]=a;}setAnswers(valid);setIndex(Number.isInteger(d.index)?Math.max(0,Math.min(list.length,d.index)):0);setRater(typeof d.rater==='string'?d.rater:'R01');}}}catch{setError('임시 저장을 불러오지 못했습니다.')}setReady(true);return()=>{if(timer.current)clearTimeout(timer.current)}},[]);
 useEffect(()=>{if(ready)try{localStorage.setItem(key,JSON.stringify({schema,mode,index,rater,answers}))}catch{setError('임시 저장이 안 됩니다. 완료 후 제출 파일을 받아주세요.')}},[ready,key,schema,mode,index,rater,answers]);
 function move(n:number){if(timer.current)clearTimeout(timer.current);lock.current=false;setIndex(n);setSaved(false);window.scrollTo({top:0});}
 function choose(value:string){if(!item||lock.current)return;lock.current=true;setAnswers(a=>({...a,[item.id]:{value,updatedAt:new Date().toISOString()}}));timer.current=setTimeout(()=>move(index+1),250);}
 const complete=tasks.every(t=>t.options.some(o=>o[0]===answers[t.id]?.value));
 function download(){if(!complete||!rater.trim())return;const payload={schema,mode,rater:rater.trim(),submittedAt:new Date().toISOString(),candidateOrder:candidates.map(c=>c.id),responses:tasks.map(t=>({id:t.id,candidate:t.candidate.id,kind:t.kind,question:t.title,answer:answers[t.id]}))};const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`${schema}-${mode}-${rater.replace(/[^a-zA-Z0-9_-]/g,'_')}-${Date.now()}.json`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);setSaved(true);}
 if(!ready)return <main className="trigger-review">불러오는 중…</main>;
 return <main className="trigger-review"><header><strong>{labels[mode]}</strong><span>{Math.min(index+1,tasks.length)} / {tasks.length}</span></header><progress aria-label="응답 진행" value={Object.keys(answers).length} max={tasks.length}/>{error&&<p role="alert">{error}</p>}
 {item?<><section className="tr-question"><h1>{item.title}</h1>{mode==='face'?<p>원래 있던 주름·모공과 귀걸이는 제외해주세요. 밝기나 위치 차이만으로 피부 무늬가 생겼다고 판단하지 마세요.</p>:<p>같은 사람으로 보이는지와 얼굴형·이목구비·표정·시선이 유지됐는지를 함께 판단해주세요. 피부의 부자연스러운 무늬는 앞 평가에서 따로 판단했습니다.</p>}</section>
 <section className={`tr-images ${mode==='face'?'crop':''}`} aria-label="비교 이미지">{(['reference','candidate'] as const).map(k=><figure key={item.id+k}><figcaption>{k==='reference'?'원본':'결과'}</figcaption><a href={mode==='face'?item.candidate[k==='reference'?'referenceCrop':'candidateCrop']:item.candidate[k]} target="_blank" rel="noreferrer"><img src={mode==='face'?item.candidate[k==='reference'?'referenceCrop':'candidateCrop']:item.candidate[k]} alt={k==='reference'?'원본':'결과'}/></a></figure>)}</section>
 <nav className="tr-answer" aria-label="응답">{item.options.map(([value,label])=><Button key={item.id+value} variant={answers[item.id]?.value===value?'default':'outline'} aria-pressed={answers[item.id]?.value===value} onClick={()=>choose(value)}>{label}</Button>)}</nav><footer><Button variant="outline" disabled={index===0} onClick={()=>move(index-1)}>← 이전 · 수정</Button>{answers[item.id]&&<Button variant="outline" onClick={()=>move(index+1)}>다음 →</Button>}</footer>
 </>:<section className="tr-finish"><h1>이 묶음의 평가가 끝났습니다.</h1><label htmlFor="rater">평가자 번호</label><input id="rater" value={rater} maxLength={40} onChange={e=>setRater(e.target.value)}/><Button disabled={!complete||!rater.trim()} onClick={download}>{saved?'제출 파일 다시 받기':'제출 파일 받기'}</Button><p>받은 파일을 이 채팅에 첨부해주세요.</p><Button variant="outline" onClick={()=>move(tasks.findIndex(t=>!answers[t.id])>=0?tasks.findIndex(t=>!answers[t.id]):tasks.length-1)}>응답 수정</Button><details><summary>다른 평가 묶음</summary>{modes.filter(m=>m!==mode).map(m=><p key={m}><a href={'/current-review?part='+m}>{labels[m]} · {makeTasks(m).length}문항</a></p>)}</details><details><summary>응답 목록</summary>{tasks.map((t,i)=><button className="tr-summary" key={t.id} onClick={()=>move(i)}>{i+1}. {t.title} — {t.options.find(o=>o[0]===answers[t.id]?.value)?.[1]||'미응답'}</button>)}</details></section>}</main>;
}
