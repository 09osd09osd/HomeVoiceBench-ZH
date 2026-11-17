"""Publish the audited, user-authorized public repository and evidence release.

Requires an existing GitHub credential (Git Credential Manager, GitHub CLI or GH_TOKEN).
No credential is printed or written to repository files. No login is initiated.
"""
import argparse,base64,datetime,hashlib,http.client,json,os,shutil,subprocess,sys,time,urllib.error,urllib.parse,urllib.request
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads(path.read_text('utf-8'))
git=os.getenv('HOMEVOICE_GIT','git');env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'Never'}
def credential():
    token=os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN')
    if token:return token
    result=subprocess.run([git,'credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,env=env,cwd=ROOT)
    values=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    if values.get('password'):return values['password']
    gh=shutil.which('gh')
    if not gh and sys.platform=='win32':
        candidate=Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'GitHub CLI/gh.exe'
        if candidate.is_file():gh=str(candidate)
    if gh:
        result=subprocess.run([gh,'auth','token','--hostname','github.com'],text=True,capture_output=True,env=env,cwd=ROOT)
        if result.returncode==0 and result.stdout.strip():return result.stdout.strip()
    raise RuntimeError('No existing GitHub credential. Sign in locally with GitHub CLI or Git Credential Manager; no token needs to be sent in chat.')
ap=argparse.ArgumentParser();ap.add_argument('--check-auth',action='store_true');args=ap.parse_args();token=credential()
headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'HomeVoiceBench-ZH'}
def api(method,route,data=None,allow404=False):
    req=urllib.request.Request('https://api.github.com'+route,method=method,headers={**headers,'Content-Type':'application/json'},data=json.dumps(data).encode() if data is not None else None)
    try:
        with urllib.request.urlopen(req,timeout=60) as response:return None if response.status==204 else json.load(response)
    except urllib.error.HTTPError as e:
        if e.code==404 and allow404:return None
        detail=e.read().decode('utf-8',errors='replace').replace(token,'[REDACTED]')
        raise RuntimeError(f'GitHub {method} {route}: HTTP {e.code}: '+detail[:800]) from None
user=api('GET','/user')
if args.check_auth:print(json.dumps({'authenticated':True,'login':user['login']}));raise SystemExit()
summary=read(ROOT/'reports/summary.json');audit=read(ROOT/'reports/release_audit.json')
if summary['evaluation_status']!='complete' or audit['status']!='passed' or audit['scope']!='complete_release':raise ValueError('Complete, audited evaluation required for publication')
assets=read(ROOT/'reports/release_assets.json')
if not assets.get('inputs') or not assets.get('evaluation'):raise ValueError('All evidence archives must be ready')
publication_path=ROOT/'reports/publication.json';record=read(publication_path) if publication_path.exists() else {}
def save():publication_path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n','utf-8')
record.pop('reason',None)
record.update(authenticated_login=user['login'],last_auth_check_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
if record.get('repository_full_name'):
    repo=api('GET','/repos/'+record['repository_full_name'])
    if repo['owner']['login'].lower()!=user['login'].lower() or repo['private']:raise ValueError('Publication repository account/visibility mismatch')
else:
    name='HomeVoiceBench-ZH'
    if api('GET',f'/repos/{user["login"]}/{name}',allow404=True):name+='-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    repo=api('POST','/user/repos',{'name':name,'description':'中文家庭纯语音交互基准：30工具场景+20聊天场景，1000题，三条模型链路和听音评分。','private':False,'auto_init':False})
    record.update(repository_full_name=repo['full_name'],repository_url=repo['html_url'],visibility='public',status='repository_created',created_at=datetime.datetime.now(datetime.timezone.utc).isoformat());save()
print(json.dumps({'repository':repo['html_url'],'visibility':'public'}),flush=True)
for script in ['build_docs.py','build_site.py','build_delivery_index.py']:
    subprocess.run([sys.executable,'-X','utf8','scripts/'+script],cwd=ROOT,check=True)
subprocess.run([git,'-c','core.safecrlf=false','add','.'],cwd=ROOT,check=True)
subprocess.run([sys.executable,'-X','utf8','scripts/check_public_files.py'],cwd=ROOT,env={**env,'HOMEVOICE_GIT':git},check=True)
subprocess.run([git,'-c','core.safecrlf=false','add','reports/public_file_audit.json'],cwd=ROOT,check=True)
changed=subprocess.run([git,'diff','--cached','--quiet'],cwd=ROOT).returncode
if changed:
    subprocess.run([git,'-c','user.name='+user['login'],'-c',f'user.email={user["id"]}+{user["login"]}@users.noreply.github.com','commit','--quiet','-m','Release HomeVoiceBench-ZH: 1000 audio cases and audited three-system evaluation'],cwd=ROOT,check=True)
remote=subprocess.run([git,'remote','get-url','origin'],cwd=ROOT,capture_output=True,text=True)
if remote.returncode:subprocess.run([git,'remote','add','origin',repo['clone_url']],cwd=ROOT,check=True)
elif remote.stdout.strip()!=repo['clone_url']:raise ValueError('Existing origin is not the authorized new repository')
push_env={**env,'GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'http.https://github.com/.extraheader','GIT_CONFIG_VALUE_0':'AUTHORIZATION: basic '+base64.b64encode(('x-access-token:'+token).encode()).decode()}
subprocess.run([git,'push','-u','origin','main'],cwd=ROOT,env=push_env,check=True)
try:
    pages=api('GET',f'/repos/{repo["full_name"]}/pages',allow404=True)
    if not pages:pages=api('POST',f'/repos/{repo["full_name"]}/pages',{'source':{'branch':'main','path':'/'}})
    record['pages_url']=pages.get('html_url');record['pages_status']=pages.get('status','build_requested')
    if record['pages_url']:api('PATCH',f'/repos/{repo["full_name"]}',{'homepage':record['pages_url']})
except Exception as e:record['pages_status']='unavailable';record['pages_error']=str(e).replace(token,'[REDACTED]')[:600]
save()
tag='v0.2.0';release=api('GET',f'/repos/{repo["full_name"]}/releases/tags/{tag}',allow404=True)
if not release:
    release=api('POST',f'/repos/{repo["full_name"]}/releases',{'tag_name':tag,'target_commitish':'main','name':'HomeVoiceBench-ZH v0.2 · 1000 audio cases','body':'包含1000道冻结题目、1648段输入语音及三条系统实际运行证据。各ZIP按内部相对路径解压至仓库根目录；SHA256见reports/release_assets.json。模型权重与密钥不分发。评分、局限及字段说明见README。','draft':True,'prerelease':False})
def list_assets():return {a['name']:a for a in api('GET',f'/repos/{repo["full_name"]}/releases/{release["id"]}/assets?per_page=100')}
def verify_asset(item,entry):
    if item.get('state')!='uploaded' or item['size']!=entry['bytes'] or item.get('digest')!='sha256:'+entry['sha256']:
        raise ValueError('Uploaded asset state, size or SHA256 mismatch: '+entry['name'])
    return {'name':entry['name'],'url':item['browser_download_url'],'sha256':entry['sha256'],'bytes':entry['bytes'],'asset_id':item['id'],'server_digest_verified':True}
def upload(entry):
    p=(ROOT/entry['path']).resolve()
    if not p.is_relative_to((ROOT/'release_parts').resolve()):raise ValueError('Upload source outside release_parts')
    with p.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
    if actual!=entry['sha256'] or p.stat().st_size!=entry['bytes']:raise ValueError('Local archive changed: '+entry['name'])
    for attempt in range(1,4):
        item=list_assets().get(entry['name'])
        if item:
            if item.get('state')=='starter' and item['size']==0 and release['draft']:
                # A failed upload can leave an empty starter placeholder. Only
                # remove that empty placeholder in this new draft release.
                api('DELETE',f'/repos/{repo["full_name"]}/releases/assets/{item["id"]}')
            else:return verify_asset(item,entry)
        address=urllib.parse.urlsplit(release['upload_url'].split('{')[0]+'?'+urllib.parse.urlencode({'name':entry['name']}))
        if address.hostname!='uploads.github.com':raise ValueError('Unexpected upload host')
        conn=http.client.HTTPSConnection(address.hostname,timeout=60)
        try:
            print(json.dumps({'upload_started':entry['name'],'attempt':attempt,'bytes':entry['bytes']}),flush=True)
            conn.putrequest('POST',address.path+'?'+address.query)
            content_type='application/zip' if p.suffix=='.zip' else 'text/plain; charset=utf-8'
            for k,v in {**headers,'Content-Type':content_type,'Content-Length':str(entry['bytes'])}.items():conn.putheader(k,v)
            conn.endheaders();sent=0;last=time.monotonic()
            with p.open('rb') as f:
                while chunk:=f.read(2*1024**2):
                    conn.send(chunk);sent+=len(chunk)
                    if time.monotonic()-last>=20:
                        print(json.dumps({'upload_progress':entry['name'],'sent_bytes':sent,'total_bytes':entry['bytes']}),flush=True);last=time.monotonic()
            result=conn.getresponse();raw=result.read()
            if result.status!=201:raise RuntimeError('Asset upload failed HTTP '+str(result.status))
            return verify_asset(json.loads(raw),entry)
        except (OSError,http.client.HTTPException,RuntimeError) as e:
            print(json.dumps({'upload_retry':entry['name'],'attempt':attempt,'error_type':type(e).__name__}),flush=True)
            if attempt==3:raise
            time.sleep(3*attempt)
        finally:conn.close()
def upload_many(entries):
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(upload,entry):entry for entry in entries}
        for future in as_completed(futures):
            item=future.result()
            recorded={x['name']:x for x in record.get('uploaded_assets',[])};recorded[item['name']]=item
            record['uploaded_assets']=list(recorded.values());save()
            print(json.dumps({'uploaded':item['name'],'bytes':item['bytes'],'verified_count':len(recorded)}),flush=True)
record.update(status='uploading',release_id=release['id']);save()
upload_many(assets['inputs']+assets['evaluation'])
release=api('PATCH',f'/repos/{repo["full_name"]}/releases/{release["id"]}',{'draft':False})
record.update(status='published',release_url=release['html_url'],commit=subprocess.check_output([git,'rev-parse','HEAD'],cwd=ROOT,text=True).strip())
try:
    pages=api('GET',f'/repos/{repo["full_name"]}/pages',allow404=True)
    if not pages:pages=api('POST',f'/repos/{repo["full_name"]}/pages',{'source':{'branch':'main','path':'/'}})
    record['pages_url']=pages.get('html_url');record['pages_status']='build_requested'
except Exception as e:record['pages_status']='unavailable';record['pages_error']=str(e).replace(token,'[REDACTED]')[:600]
save()
for script in ['build_docs.py','build_site.py','build_delivery_index.py']:
    subprocess.run([sys.executable,'-X','utf8','scripts/'+script],cwd=ROOT,check=True)
def commit_and_push(message):
    subprocess.run([git,'-c','core.safecrlf=false','add','.'],cwd=ROOT,check=True)
    subprocess.run([sys.executable,'-X','utf8','scripts/check_public_files.py'],cwd=ROOT,env={**env,'HOMEVOICE_GIT':git},check=True)
    subprocess.run([git,'-c','core.safecrlf=false','add','reports/public_file_audit.json'],cwd=ROOT,check=True)
    if subprocess.run([git,'diff','--cached','--quiet'],cwd=ROOT).returncode:
        subprocess.run([git,'-c','user.name='+user['login'],'-c',f'user.email={user["id"]}+{user["login"]}@users.noreply.github.com','commit','--quiet','-m',message],cwd=ROOT,check=True)
        subprocess.run([git,'push','origin','main'],cwd=ROOT,env=push_env,check=True)
commit_and_push('Link public benchmark release and explanation website')
if 'homevoicebench-zh-v0.2-source.zip' not in list_assets():
    subprocess.run([sys.executable,'-X','utf8','scripts/package_source.py'],cwd=ROOT,env={**env,'HOMEVOICE_GIT':git},check=True)
source=read(ROOT/'reports/source_archive.json');record['source_archive']=source;save()
subprocess.run([sys.executable,'-X','utf8','scripts/build_delivery_index.py'],cwd=ROOT,check=True)
extras=[source]
for name in ['SHA256SUMS.txt','README.md']:
    p=ROOT/'release_parts'/name
    extras.append({'name':name,'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
upload_many(extras)
actual=list_assets()
for entry in assets['inputs']+assets['evaluation']+extras:verify_asset(actual[entry['name']],entry)
record.update(release_asset_count=len(actual),all_assets_verified_at=datetime.datetime.now(datetime.timezone.utc).isoformat());save()
commit_and_push('Record verified release checksums and source archive')
print(json.dumps({k:record.get(k) for k in ['status','repository_url','release_url','pages_url','pages_status']},ensure_ascii=False))
