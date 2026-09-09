const $=s=>document.querySelector(s);let boot,projectId=localStorage.getItem('studio-project'),dirty=false,working=false,lastJob='';
const labels={original:'원본 유지',none:'없음',navy:'남색',white:'흰색',black:'검정',gray:'회색',silver:'은색',gold:'금색','pale blue':'옅은 파란색',studio:'스튜디오',ocean:'바다',garden:'정원',red:'빨강',blue:'파랑'};
const display=v=>labels[v]||v;
const stored=v=>Object.keys(labels).find(k=>labels[k]===v.trim())||v.trim();
const title=p=>p.name==='연구 샘플 P04'?'샘플 이미지':p.name;
const media=(p,f)=>'/media/'+p.id+'/'+f;
const current=()=>boot?.projects.find(p=>p.id===projectId);
function note(t,error=false){$('#status').textContent=t;$('#status').classList.toggle('error',error)}
async function api(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Studio-Token':boot.token},body:JSON.stringify(body)});const d=await r.json();if(!r.ok)throw Error(d.error||'요청 실패');return d}
function choose(id){projectId=id;localStorage.setItem('studio-project',id);dirty=false;note('');render()}
function button(text,cls,fn){let e=document.createElement('button');e.textContent=text;e.className=cls;e.onclick=fn;return e}
function render(){const p=current(),busy=working||!!p?.active_job;$('#empty').hidden=!!p;$('#canvas').hidden=!p;$('#title').textContent=p?title(p):'이미지 편집';$('#projects').replaceChildren(...boot.projects.map(x=>button(title(x),'project '+(x.id===projectId?'selected':''),()=>choose(x.id))));$('#versions').replaceChildren();$('#messages').replaceChildren();
if(p){$('#original').src=media(p,'reference.png');const v=p.versions.find(v=>v.id===p.current_version);$('#result').src=media(p,v?v.image:'reference.png');$('#result-label').textContent=v?'버전 '+(p.versions.indexOf(v)+1):'미리보기';$('#download').hidden=!v;$('#download').href=v?media(p,v.image):'#';if(!dirty)for(const k of Object.keys(p.state))$('#settings').elements[k].value=display(p.state[k]);
for(const [i,v]of [...p.versions.entries()].reverse()){let b=button('버전 '+(i+1)+' · '+new Date(v.created*1000).toLocaleTimeString('ko-KR'), 'version '+(v.id===p.current_version?'selected':''),()=>act(async()=>{await api('/api/restore',{project:p.id,revision:p.revision,version:v.id});dirty=false;note('복원 완료')}));b.disabled=busy;$('#versions').append(b)}
for(const m of p.messages.slice(-6)){let e=document.createElement('div');e.className='message';e.textContent=m.request;let small=document.createElement('small');small.textContent=m.applied===false?m.reply:Object.values(m.state).map(display).join(' · ');e.append(small);$('#messages').append(e)}
if(p.active_job){let j=boot.jobs[p.active_job];note((j?.kind==='chat'?'요청 반영 중':'생성 중')+' '+Math.floor(Date.now()/1000-(j?.started||Date.now()/1000))+'초');lastJob=p.active_job}else if(lastJob&&boot.jobs[lastJob]?.project===p.id){const j=boot.jobs[lastJob];if(j.status!=='running'){note(j.message,j.status==='error');lastJob=''}}
}else{$('#download').hidden=true;for(const e of $('#settings').querySelectorAll('input'))e.value=''}
for(const e of document.querySelectorAll('#settings input,#settings button,#chat textarea,#chat button,#generate'))e.disabled=!p||busy;$('#generate').disabled=!p||busy||dirty;
}
async function refresh(){boot=await(await fetch('/api/bootstrap')).json();if(!current()&&boot.projects.length)projectId=boot.projects[0].id;render()}
async function act(fn){if(working)return;working=true;render();try{await fn();await refresh()}catch(e){note(e.message,true)}finally{working=false;render()}}
$('#settings').oninput=()=>{dirty=true;$('#generate').disabled=true;note('수정한 설정을 저장해주세요.')};
$('#settings').onsubmit=e=>{e.preventDefault();act(async()=>{let p=current();let state=Object.fromEntries([...new FormData(e.target)].map(([k,v])=>[k,stored(v)]));await api('/api/state',{project:p.id,revision:p.revision,state});dirty=false;note('저장 완료')})};
$('#chat').onsubmit=e=>{e.preventDefault();if(dirty){note('직접 수정한 설정부터 저장해주세요.',true);return}act(async()=>{let p=current();await api('/api/chat',{project:p.id,revision:p.revision,request:$('#request').value});$('#request').value=''})};
$('#generate').onclick=()=>act(async()=>{let p=current();await api('/api/generate',{project:p.id,revision:p.revision})});
$('#sample').onclick=()=>act(async()=>{let p=await api('/api/create',{sample:true});projectId=p.id;dirty=false;localStorage.setItem('studio-project',p.id);note('')});
$('#file').onchange=e=>act(async()=>{let f=e.target.files[0];if(!f)return;if(f.size>15000000)throw Error('15MB 이하 파일을 선택해주세요.');let image=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(f)});let p=await api('/api/create',{image,name:f.name});projectId=p.id;dirty=false;localStorage.setItem('studio-project',p.id);note('')});
refresh().catch(e=>note('편집기에 연결하지 못했습니다. '+e.message,true));setInterval(()=>{if(!working)refresh().catch(()=>{})},2000);
