'use client';
import {useState} from 'react';
import {Button} from '@/components/ui/button';

const requests=['양쪽 귀에 작은 은색 링 귀걸이','얇은 은색 목걸이와 작은 원형 은색 펜던트','화면 오른쪽 가슴에 작은 버건디 원형 핀 하나','남색 재킷과 아이보리 라운드넥 셔츠','현대적 사무실 배경','기존 핀을 코발트 파란색으로 변경','기존 펜던트를 작은 은색 물방울 모양으로 변경','기존 재킷을 차콜 회색으로 변경','화면 왼쪽 가슴 주머니에 버건디 포켓스퀘어 — 핀 반대편','나무 책장이 있는 조용한 도서관 배경'];
export default function Trajectory(){
 const [stage,setStage]=useState(1);
 return <main className="workspace">
  <header><h1>10단계 순차 편집</h1><span>{stage} / 10</span></header>
  <nav aria-label="단계 선택" style={{display:'flex',gap:8,flexWrap:'wrap'}}>{requests.map((_,i)=><Button key={i} variant={stage===i+1?'default':'outline'} aria-pressed={stage===i+1} onClick={()=>setStage(i+1)}>{i+1}단계</Button>)}</nav>
  <section className="question"><h1>{requests[stage-1]}</h1></section>
  <section className="trajectory-pair">
   <figure><h2>원본</h2><a href="/ten-stage/reference.png" target="_blank" rel="noreferrer"><img src="/ten-stage/reference.png" alt="편집 전 원본 인물"/></a></figure>
   <figure><h2>{stage}단계 결과</h2><a href={`/ten-stage/step-${stage}.png`} target="_blank" rel="noreferrer"><img src={`/ten-stage/step-${stage}.png`} alt={`${stage}단계 편집 결과`}/></a></figure>
  </section>
  <footer><Button variant="outline" disabled={stage===1} onClick={()=>setStage(stage-1)}>이전</Button><Button disabled={stage===10} onClick={()=>setStage(stage+1)}>다음</Button></footer>
 </main>;
}
