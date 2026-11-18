"""Audit exact staged v0.4 bytes; original release files are not modified."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import CODE_ROOT as CODE,SHARED_ROOT
from homevoice.cloud import load_key
keys=[load_key(s).encode() for s in ['bailian','deepseek']]
names=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=SHARED_ROOT).decode('utf-8').split('\0');names=[n for n in names if n]
issues=[];hashes={};total=0
reader=subprocess.Popen(['git','cat-file','--batch'],cwd=SHARED_ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
def index_bytes(name):
    if '\n' in name or '\r' in name:raise ValueError('Unexpected newline in staged path')
    reader.stdin.write((':'+name+'\n').encode('utf-8'));reader.stdin.flush()
    header=reader.stdout.readline().split()
    if len(header)!=3 or header[1]!=b'blob':raise ValueError('Missing staged blob: '+name)
    size=int(header[2]);data=reader.stdout.read(size)
    if len(data)!=size or reader.stdout.read(1)!=b'\n':raise ValueError('Incomplete staged blob')
    return data
for name in names:
    if not(name.startswith('versions/v0.4/') or name in ['docs/REVISION_v0.4_PLAN.md','scripts/bootstrap_v04.py']):issues.append({'path':name,'reason':'outside authorized additive revision'});continue
    if set(Path(name).parts)&{'.local','models','runtime','cache','runs','assets','logs','pilot_history','release_parts','human_calibration'}:issues.append({'path':name,'reason':'runtime/private/bulky file staged'});continue
    data=index_bytes(name);total+=len(data);hashes[name]=hashlib.sha256(data).hexdigest()
    if len(data)>95*1024**2:issues.append({'path':name,'reason':'file too large for Git'})
    if any(k in data for k in keys) or re.search(rb'\bsk-[A-Za-z0-9]{24,}\b|sk-ws-[A-Za-z0-9._-]{25,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',data):issues.append({'path':name,'reason':'credential pattern'})
for split in ['pilot','benchmark']:
    manifest=json.loads((CODE/split/'data/manifest.json').read_text('utf-8'))
    for c in manifest['cases']:
        name=f'versions/v0.4/{split}/'+c['path'];digest=hashes.get(name)
        if digest is None:digest=hashlib.sha256(index_bytes(name)).hexdigest()
        if digest!=c['sha256']:issues.append({'path':name,'reason':'frozen case bytes mismatch'})
reader.stdin.close();reader.wait(timeout=10)
out={'status':'failed' if issues else 'passed','staged_files':len(names),'bytes':total,'issues':issues,'frozen_cases_checked':1100,'scope':'exact Git index; additive v0.4 files only'}
folder=CODE/'reports';folder.mkdir(exist_ok=True);(folder/'public_file_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(out,ensure_ascii=False));raise SystemExit(1 if issues else 0)
