"""Publish the user-authorized additive v0.4 release after complete verification."""
import base64,concurrent.futures,hashlib,http.client,json,os,shutil,subprocess,sys,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import CODE_ROOT as CODE,SHARED_ROOT as REPO
REPOSITORY='09osd09osd/HomeVoiceBench-ZH';TAG='v0.4.0'
def read(p):return json.loads(p.read_text('utf-8'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),'utf-8')
for split in ['pilot','benchmark']:
    if read(CODE/split/'reports/acceptance.json')['status']!='passed':raise ValueError('Complete technical acceptance required')
if read(CODE/'docs/PRESERVATION.json')['status']!='passed':raise ValueError('Original data, results and audio preservation must pass')
assets=[x for part in ['inputs','evaluation','history'] for x in read(CODE/'reports'/f'release_assets_{part}.json')]
for a in assets:
    with (CODE/a['path']).open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=a['sha256']:raise ValueError('Archive bytes changed')
env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'Never'}
token=os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN')
if not token:
    r=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,cwd=REPO,env=env)
    token=dict(s.split('=',1) for s in r.stdout.splitlines() if '=' in s).get('password')
if not token:raise RuntimeError('Existing GitHub login is unavailable')
headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'HomeVoiceBench-ZH-v0.4'}
def api(method,path,data=None,allow404=False):
    req=urllib.request.Request('https://api.github.com'+path,method=method,headers={**headers,'Content-Type':'application/json'},data=json.dumps(data,ensure_ascii=False).encode() if data is not None else None)
    try:
        with urllib.request.urlopen(req,timeout=90) as r:return json.load(r) if r.status!=204 else None
    except urllib.error.HTTPError as e:
        if allow404 and e.code==404:return None
        raise RuntimeError(f'GitHub {method} {path}: HTTP {e.code}') from None
user=api('GET','/user');repo=api('GET','/repos/'+REPOSITORY)
if user['login']!='09osd09osd' or repo['private']:raise ValueError('Unexpected GitHub identity/repository visibility')
origin=subprocess.check_output(['git','remote','get-url','origin'],cwd=REPO,text=True).strip()
if origin!='https://github.com/'+REPOSITORY+'.git':raise ValueError('Origin mismatch')
subprocess.run(['git','-c','core.safecrlf=false','add','--','versions/v0.4','docs/REVISION_v0.4_PLAN.md','scripts/bootstrap_v04.py'],cwd=REPO,check=True)
subprocess.run([sys.executable,'-X','utf8',str(CODE/'scripts/audit_public_v04.py')],cwd=CODE,check=True)
subprocess.run(['git','add','--','versions/v0.4/reports/public_file_audit.json'],cwd=REPO,check=True)
if subprocess.run(['git','diff','--cached','--quiet'],cwd=REPO).returncode:
    subprocess.run(['git','-c','user.name='+user['login'],'-c',f'user.email={user["id"]}+{user["login"]}@users.noreply.github.com','commit','-m','Add v0.4: 1000 audio cases, greedy systems, compact tools and objective plus audio scoring'],cwd=REPO,check=True)
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
push_env={**env,'GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'http.https://github.com/.extraheader','GIT_CONFIG_VALUE_0':'AUTHORIZATION: basic '+base64.b64encode(('x-access-token:'+token).encode()).decode()}
subprocess.run(['git','push','origin','main'],cwd=REPO,env=push_env,check=True)
release=api('GET',f'/repos/{REPOSITORY}/releases/tags/{TAG}',allow404=True)
body='v0.4独立正式1000题：600工具题+400聊天题、40%成组题、70%为1–2轮；三组内容与工具决策均greedy。工具精简为10+2。程序状态/授权检查与指定模型实际听音结合，分歧按预先固定规则重新听音裁定；尚未完成人工校准。原v0.3和两个开发阶段存档保留。先下载或克隆本仓库，再将所有inputs和evaluation ZIP解压至仓库根目录；history ZIP为两轮开发存档。题目JSON、代码、规范、报告和Excel位于versions/v0.4；附件补充输入/输出音频、三组执行轨迹和评分证据。SHA256见versions/v0.4/reports/release_assets_*.json。不含模型权重或密钥。'
if not release:release=api('POST',f'/repos/{REPOSITORY}/releases',{'tag_name':TAG,'target_commitish':commit,'name':'HomeVoiceBench-ZH v0.4 · 1000 audio cases','body':body,'draft':True,'prerelease':False})
source_commit=release['target_commitish'] if release['target_commitish']!='main' else commit
if source_commit!=commit:
    if subprocess.run(['git','merge-base','--is-ancestor',source_commit,commit],cwd=REPO).returncode:raise ValueError('Existing release source is not an ancestor of current code')
    if subprocess.run(['git','diff','--quiet',source_commit,commit,'--','versions/v0.4/homevoice','versions/v0.4/scripts','versions/v0.4/spec','versions/v0.4/benchmark/data/cases','versions/v0.4/pilot/data/cases'],cwd=REPO).returncode:raise ValueError('Existing release source differs in executable code or frozen cases')
def listed():return {a['name']:a for a in api('GET',f'/repos/{REPOSITORY}/releases/{release["id"]}/assets?per_page=100')}
def matches(remote,a):return remote.get('state')=='uploaded' and remote['size']==a['bytes'] and remote.get('digest')=='sha256:'+a['sha256']
existing=listed()
def upload(a):
    if a['name'] in existing:
        if not matches(existing[a['name']],a):raise ValueError('Asset name exists with different bytes: '+a['name'])
        return existing[a['name']]
    url=urllib.parse.urlsplit(release['upload_url'].split('{')[0]+'?name='+urllib.parse.quote(a['name']))
    if url.hostname!='uploads.github.com':raise ValueError('Unexpected upload host')
    for attempt in range(3):
        connection=http.client.HTTPSConnection(url.hostname,timeout=180)
        try:
            connection.putrequest('POST',url.path+'?'+url.query)
            for k,v in {**headers,'Content-Type':'application/zip','Content-Length':str(a['bytes'])}.items():connection.putheader(k,v)
            connection.endheaders()
            sent=0;next_report=32*1024**2
            with (CODE/a['path']).open('rb') as f:
                while chunk:=f.read(1024**2):
                    connection.send(chunk);sent+=len(chunk)
                    if sent>=next_report:
                        print(json.dumps({'uploading':a['name'],'sent_mib':round(sent/1024**2,1),'total_mib':round(a['bytes']/1024**2,1)}),flush=True);next_report+=32*1024**2
            response=connection.getresponse();data=json.loads(response.read())
            if response.status==201 and matches(data,a):print(json.dumps({'uploaded':a['name'],'bytes':a['bytes']}),flush=True);return data
        except (OSError,http.client.HTTPException,TimeoutError):pass
        finally:connection.close()
        found=listed().get(a['name'])
        if found and matches(found,a):return found
        if found:raise ValueError('Incomplete or different asset requires inspection: '+a['name'])
        time.sleep(2+attempt*3)
    raise RuntimeError('Upload did not complete: '+a['name'])
with concurrent.futures.ThreadPoolExecutor(3) as pool:uploaded=list(pool.map(upload,assets))
check=listed()
if any(not matches(check.get(a['name'],{}),a) for a in assets):raise ValueError('Remote asset verification failed')
release=api('PATCH',f'/repos/{REPOSITORY}/releases/{release["id"]}',{'draft':False,'body':body})
record={'status':'published','repository_url':repo['html_url'],'release_url':release['html_url'],'release_id':release['id'],'source_commit':source_commit,'public':True,'assets':[{'name':a['name'],'bytes':a['bytes'],'sha256':a['sha256'],'url':f'https://github.com/{REPOSITORY}/releases/download/{TAG}/'+a['name'],'server_digest_verified':True} for a in assets],'human_calibration_performed':False,'old_release_preserved':True}
save(CODE/'reports/publication.json',record);subprocess.run(['git','add','--','versions/v0.4/reports/publication.json'],cwd=REPO,check=True)
if subprocess.run(['git','diff','--cached','--quiet'],cwd=REPO).returncode:
    subprocess.run(['git','-c','user.name='+user['login'],'-c',f'user.email={user["id"]}+{user["login"]}@users.noreply.github.com','commit','-m','Record verified v0.4 release assets'],cwd=REPO,check=True)
subprocess.run(['git','push','origin','main'],cwd=REPO,env=push_env,check=True)
print(json.dumps({'release_url':release['html_url'],'asset_count':len(assets),'verified':True}),flush=True)
