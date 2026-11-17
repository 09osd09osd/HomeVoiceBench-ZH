"""Check only explicitly staged/tracked files before public publication."""
import hashlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from homevoice.cloud import load_key
git=os.getenv('HOMEVOICE_GIT','git')
names=subprocess.check_output([git,'ls-files','-z'],cwd=ROOT).decode('utf-8').split('\0');names=[n for n in names if n]
if not names:raise ValueError('No explicit Git file set to check')
secrets=[]
for provider in ['bailian','deepseek']:
    try:secrets.append(load_key(provider).encode())
    except Exception:pass
for key in ['GH_TOKEN','GITHUB_TOKEN']:
    if os.getenv(key):secrets.append(os.environ[key].encode())
problems=[];total=0;indexed_hashes={}
proc=subprocess.Popen([git,'cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
def index_blob(name):
    proc.stdin.write((':'+name+'\n').encode());proc.stdin.flush();head=proc.stdout.readline().decode().strip().split()
    if len(head)!=3 or head[1]!='blob':raise ValueError('Expected staged blob: '+name)
    size=int(head[2]);data=proc.stdout.read(size)
    if len(data)!=size or proc.stdout.read(1)!=b'\n':raise ValueError('Incomplete staged blob: '+name)
    return data
for name in names:
    p=ROOT/name
    if not p.resolve().is_relative_to(ROOT.resolve()):problems.append({'path':name,'reason':'outside project'});continue
    if name.split('/')[0] in ['.local','models','runtime','cache','runs','assets','logs','release_parts'] or p.suffix in ['.gguf','.safetensors','.pt','.pth','.zip']:
        problems.append({'path':name,'reason':'private or bulky runtime artifact'});continue
    data=index_blob(name);indexed_hashes[name]=hashlib.sha256(data).hexdigest();total+=len(data)
    if len(data)>=95*1024**2:problems.append({'path':name,'reason':'too large for Git history'});continue
    if any(secret and secret in data for secret in secrets):problems.append({'path':name,'reason':'exact configured credential match'})
    if p.suffix in ['.json','.jsonl','.md','.html','.txt','.py','.mjs']:
        text=data.decode('utf-8',errors='replace')
        if re.search(r'sk-ws-[A-Za-z0-9._-]{25,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|[?&](?:X-Amz-Signature|access_token|api_key)=[A-Za-z0-9%._-]{16,}',text):problems.append({'path':name,'reason':'credential/signed URL pattern'})
proc.stdin.close();proc.wait(15)
report={'status':'failed' if problems else 'passed','file_count':len(names),'bytes':total,'problems':problems,'exact_key_check':bool(secrets),'scanned_content':'exact_git_index_blobs','file_set_sha256':hashlib.sha256('\n'.join(names).encode()).hexdigest()}
manifest=json.loads((ROOT/'data/manifest.json').read_text('utf-8'));checked=0
for entry in manifest['cases']:
    if indexed_hashes.get(entry['path'])!=entry['file_sha256']:problems.append({'path':entry['path'],'reason':'Git index changed or omitted frozen file bytes'})
    checked+=1
report.update(status='failed' if problems else 'passed',frozen_case_git_bytes_checked=checked)
(ROOT/'reports/public_file_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8');print(json.dumps(report,ensure_ascii=False))
if problems:raise SystemExit(1)
