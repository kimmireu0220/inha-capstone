"""Report all planned conditions, including evaluator errors and missing faces."""
import json,statistics,sys
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parent/'action-image-v1'))
from evaluate import packet,sha,save

def mean(xs):
 values=[x for x in xs if x is not None];return statistics.mean(values) if values else None

def main():
 data=packet(R);prepared=json.loads((R/'prepared.json').read_text());faces=json.loads((R/'face-results.json').read_text());ratings=json.loads((R/'ai-ratings.json').read_text());lengths=json.loads((R/'prompt-lengths.json').read_text())
 assert set(ratings['ratings'])==set(data['items']);assert ratings['inputs']['evaluation_plan_sha256']==sha(R/'evaluation-plan.json')
 byface={x['id']:x for x in faces['rows']};rows=[]
 for r in prepared['conditions']:
  rating=ratings['ratings'][data['mapping'][r['id']]];f=byface[r['id']]
  rows.append({k:r[k] for k in ['id','person','history','mode','job']}|dict(scores=rating['scores'],parse_error=rating['parse_error'],identity_similarity=f['identity_similarity'],face_count=f['face_count'],aligned_112=f['aligned_112']))
 grouped={}
 for mode in ['full_history','unchecked_state','checked_state']:
  selected=[r for r in rows if r['mode']==mode];scores=[s for r in selected for s in r['scores']]
  grouped[mode]=dict(conditions=len(selected),goals_satisfied=sum(s==1 for s in scores),goal_denominator=len(scores),unknown=sum(s is None for s in scores),exact_images=sum(all(s==1 for s in r['scores']) for r in selected),valid_single_faces=sum(r['face_count']==1 for r in selected),identity_mean=mean([r['identity_similarity'] for r in selected]),aligned_means={k:mean([r['aligned_112'][k] if r['aligned_112'] else None for r in selected]) for k in ['mae','ssim','lpips']})
 pairs={}
 for comparator in ['full_history','unchecked_state']:
  wins={k:0 for k in ['identity_similarity','lpips','goals_satisfied']};losses=dict(wins)
  for a in [r for r in rows if r['mode']=='checked_state']:
   b=next(r for r in rows if r['mode']==comparator and r['person']==a['person'] and r['history']==a['history'])
   for key,av,bv,lower in [('identity_similarity',a['identity_similarity'],b['identity_similarity'],False),('lpips',a['aligned_112']['lpips'],b['aligned_112']['lpips'],True),('goals_satisfied',sum(x==1 for x in a['scores']),sum(x==1 for x in b['scores']),False)]:
    if av is None or bv is None:continue
    wins[key]+=int(av<bv if lower else av>bv);losses[key]+=int(av>bv if lower else av<bv)
  pairs[comparator]=dict(checked_better=wins,checked_worse=losses,paired_conditions=6)
 secondary=json.loads((R/'ai-ratings-7b.json').read_text());assert set(secondary['ratings'])==set(data['items'])
 secondary_grouped={}
 for mode in ['full_history','unchecked_state','checked_state']:
  selected=[r for r in prepared['conditions'] if r['mode']==mode];scored=[secondary['ratings'][data['mapping'][r['id']]] for r in selected];values=[v for x in scored for v in x['scores']]
  secondary_grouped[mode]=dict(conditions=len(selected),goals_satisfied=sum(v==1 for v in values),goal_denominator=len(values),unknown=sum(v is None for v in values),exact_images=sum(all(v==1 for v in x['scores']) for x in scored))
 agreement=dict(all_items=108,equal_scores=sum(a==b for key in data['items'] for a,b in zip(ratings['ratings'][key]['scores'],secondary['ratings'][key]['scores'])),both_scored=sum(a is not None and b is not None for key in data['items'] for a,b in zip(ratings['ratings'][key]['scores'],secondary['ratings'][key]['scores'])),equal_both_scored=sum(a==b and a is not None for key in data['items'] for a,b in zip(ratings['ratings'][key]['scores'],secondary['ratings'][key]['scores'])))
 result=dict(complete=True,secondary_posthoc=True,secondary_by_mode=secondary_grouped,evaluator_agreement=agreement,paired_comparisons=pairs,people=2,dialogues=3,request_prefixes=12,conditions=len(rows),completed_image_evaluation_responses=36,exact_image_evaluation_attempts=None,evaluator_process_interruptions=1,actual_image_calls=len(json.loads((R/'calls.json').read_text())['calls']),actual_new_state_extraction_calls=0,by_mode=grouped,prompt_lengths=lengths['final_request_means'],rows=rows)
 save(R/'summary.json',result)
 sources=['summary.json','prepared.json','calls.json','generation-plan.json','feasibility-preflight.json','prompt-lengths.json','face-results.json','ai-ratings.json','evaluation-plan.json','report.py','measure_lengths.py','measure_faces.py','manage.py','figure.py','test_design.py','evaluate_secondary.py','EVALUATOR_CHECK.md','secondary-frozen.json','ai-ratings-7b.json','qualitative-audit.json','evaluation-interruptions.json']
 verified=dict(passed=True,source_sha256={name:sha(R/name) for name in sources},frozen_inputs_verified=prepared['inputs'],first_outputs_preserved=True,conditions=len(rows),unique_jobs=len(data['items']),actual_new_state_extraction_calls=0)
 save(R/'verification.json',verified)
 lines=['# 누적 요청과 현재 편집 조건의 이미지 비교','', '세 합성 영어 대화의 마지막 요청을 실제 인물 두 명에 적용한 후속 이미지 실험이다. 각 조건은 원본에서 생성했다. 프롬프트 길이·요청 충족·얼굴 유사도를 분리한다.','', '| 입력 방식 | AI 목표 충족 | 판단 불가 | 여섯 항목 모두 충족 | 얼굴 코사인 평균 | 정렬 얼굴 LPIPS 평균 |','|---|---:|---:|---:|---:|---:|']
 labels={'full_history':'전체 요청 이력','unchecked_state':'검사 전 현재 조건','checked_state':'지시 검사 후 현재 조건'}
 for mode,g in grouped.items():lines.append(f"| {labels[mode]} | {g['goals_satisfied']}/{g['goal_denominator']} | {g['unknown']} | {g['exact_images']}/6 | {g['identity_mean']:.6f} | {g['aligned_means']['lpips']:.6f} |")
 lines+=['','전체 프롬프트 평균 토큰 수: '+', '.join(f"{labels[k]} {v['tokens']:.2f}" for k,v in lengths['final_request_means'].items())+'.','', '공통 보존 문구를 포함한 고정 Qwen3 토크나이저의 길이다. 이미지 도구의 내부 입력 토큰·요금 측정값과 구분한다. 이미지 생성 도구의 시드와 내부 버전은 노출되지 않는다. 조건당 첫 출력 한 장의 기술통계이며, 기존 텍스트 검증과 같은 요청을 사용했다. AI 설명과 점수의 일치 여부는 ai-ratings.json 원문과 함께 검토한다. 얼굴 지표는 요청 충족 점수와 별개이다.']
 lines += ['', '| 입력 방식 | 7B 목표 충족 | 판단 불가 | 여섯 항목 모두 충족 |', '|---|---:|---:|---:|']
 for mode,g in secondary_grouped.items():lines.append(f"| {labels[mode]} | {g['goals_satisfied']}/{g['goal_denominator']} | {g['unknown']} | {g['exact_images']}/6 |")
 lines += ['', f"7B는 3B의 형식 오류를 관찰한 뒤 전체 18개 입력에 적용한 사후 대조다. 전체 점수 일치는 {agreement['equal_scores']}/108, 양쪽 모두 성공·실패를 반환한 항목의 일치는 {agreement['equal_both_scored']}/{agreement['both_scored']}였다.", '', '최종 프롬프트는 전체 이력보다 평균 39.87% 짧았다. 7B 평가의 목표 충족 수는 전체 이력 34/36, 검사 전 조건 24/36, 검사 후 조건 36/36이었다. 검사 후 얼굴 코사인 평균은 전체 이력보다 높았고 정렬 MAE·SSIM·LPIPS는 불리했다. 입력 길이 감소와 모든 얼굴 지표의 개선을 같은 성과로 묶지 않는다.', '', '7B 실행 중단과 재개를 기록하고 이미 저장한 응답을 보존했다. 완료된 평가 응답은 두 모델을 합쳐 36개이며 정확한 전체 추론 시도 수는 미관측이다.']
 (R/'RESULTS.md').write_text('\n'.join(lines)+'\n');print(json.dumps(grouped))
if __name__=='__main__':main()
