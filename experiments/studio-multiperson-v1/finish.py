"""Finalize a running batch; retain a failure report if its runner exits early."""
import json,os,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parent;REPO=R.parents[1]
pid=int(sys.argv[1]) if len(sys.argv)>1 else None
while True:
 state=json.loads((R/'running.json').read_text()) if (R/'running.json').exists() else {}
 if state.get('status')=='complete':break
 if pid:
  try:os.kill(pid,0)
  except ProcessLookupError:
   time.sleep(2)
   state=json.loads((R/'running.json').read_text())
   if state.get('status')=='complete':break
   state.update(status='interrupted',detail='Runner exited before completion; inspect runner.log and resume run.py.')
   (R/'running.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
   subprocess.run([str(REPO/'.venv-metrics/bin/python'),str(R/'analyze.py')],cwd=REPO,check=True)
   sys.exit(1)
 time.sleep(15)
subprocess.run([str(REPO/'.venv-metrics/bin/python'),str(R/'analyze.py')],cwd=REPO,check=True)
result=json.loads((R/'results.json').read_text());assert result['complete']
p=REPO/'RESEARCH_INDEX.md';s=p.read_text();s=s.replace('웹 편집기 다인물 확대 비교: 6명·3시드, 실행 중','웹 편집기 다인물 확대 비교: 6명·3시드·72장');p.write_text(s)
print('COMPLETE: 72 outputs, 18 verified pairs; results and comparison sheets saved.',flush=True)
