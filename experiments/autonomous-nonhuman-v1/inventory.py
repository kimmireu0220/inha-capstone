"""Record artifact hashes and check local Markdown links after report generation."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
NAMES=['edit-order-v1','edit-replication-v1','edit-factors-v1','nochange-extension-v1','autonomous-nonhuman-v1']

def main():
    reports=[];broken=[];count=0
    for name in NAMES:
        folder=ROOT.parent/name
        for p in folder.glob('*.md'):
            reports.append(p)
    for p in reports:
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            if '://' in target or target.startswith('#'):continue
            target=unquote(target.split('#',1)[0]);count+=1
            if not (p.parent/target).exists():broken.append({'file':str(p.relative_to(REPO)),'target':target})
    assert not broken,broken
    total=0
    for name in NAMES:
        folder=ROOT.parent/name
        files={str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='artifacts-sha256.json'}
        (folder/'artifacts-sha256.json').write_text(json.dumps({'files':files,'note':'Hash inventory excludes itself and Python bytecode caches.'},indent=2)+'\n')
        for relative,digest in files.items():assert hashlib.sha256((folder/relative).read_bytes()).hexdigest()==digest
        total+=len(files)
    print(json.dumps({'artifact_files_hashed':total,'markdown_local_links_checked':count,'broken_links':broken}))

if __name__=='__main__':main()
