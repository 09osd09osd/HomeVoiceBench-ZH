"""Download pinned public runtime/ASR. Convert original HF weights separately."""
import concurrent.futures, hashlib, json, pathlib, subprocess, sys, time, urllib.request, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from homevoice.paths import model_path
RUNTIME=ROOT/'runtime/llama-b11552';RUNTIME.mkdir(parents=True,exist_ok=True)
MODELS=ROOT/'models';MODELS.mkdir(exist_ok=True)
HEAD={'User-Agent':'HomeVoiceBench-ZH'}
def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url,headers=HEAD),timeout=90)
def download(url,path,digest=None,size=None):
    path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and (digest is None or hashlib.file_digest(path.open('rb'),'sha256').hexdigest()==digest): return
    tmp=path.with_suffix(path.suffix+'.part')
    if size and size>32*1024*1024:
        chunks=path.parent/(path.name+'.chunks');chunks.mkdir(exist_ok=True)
        chunk_size=4*1024*1024
        def piece(start):
            end=min(size-1,start+chunk_size-1);part=chunks/str(start)
            if part.exists() and part.stat().st_size==end-start+1:return part
            for attempt in range(4):
                try:
                    req=urllib.request.Request(url+f'?homevoice_part={start}',headers={**HEAD,'Range':f'bytes={start}-{end}'})
                    with urllib.request.urlopen(req,timeout=45) as source:
                        if source.status!=206:raise ValueError('server ignored byte range')
                        data=source.read()
                    if len(data)!=end-start+1:raise ValueError('incomplete byte range')
                    part.write_bytes(data);return part
                except Exception:
                    if attempt==3:raise
                    time.sleep(2**attempt)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:parts=list(pool.map(piece,range(0,size,chunk_size)))
        with tmp.open('wb') as out:
            for p in parts:out.write(p.read_bytes())
        if digest and hashlib.file_digest(tmp.open('rb'),'sha256').hexdigest()!=digest:raise ValueError('range download checksum mismatch')
        tmp.replace(path);print(json.dumps({'downloaded':path.name,'bytes':size}),flush=True);return
    for attempt in range(4):
        try:
            with fetch(url) as source,tmp.open('wb') as out:
                while block:=source.read(4*1024*1024):out.write(block)
            if digest and hashlib.file_digest(tmp.open('rb'),'sha256').hexdigest()!=digest: raise ValueError('checksum mismatch')
            tmp.replace(path);return
        except Exception:
            if attempt==3:raise
            time.sleep(2**attempt)
def llama():
    d=json.loads((ROOT/'configs/runtime_sources.json').read_text('utf-8'))
    selected=[a for a in d['assets'] if a['name']=='llama-b11552-bin-win-cuda-13.4-x64.zip']
    # Copy compatible CUDA 13 shared libraries only from the configured directory.
    for name in ['cublas64_13.dll','cublasLt64_13.dll','cudart64_13.dll']:
        target=RUNTIME/name
        if not target.exists():
            import shutil
            source=model_path('cuda_library_dir')/name
            if not source.exists():raise FileNotFoundError('Place official CUDA 13 libraries in runtime/cuda or configure cuda_library_dir: '+name)
            shutil.copy2(source,target)
    for a in selected:
        archive=ROOT/'cache'/a['name'];digest=(a.get('digest') or '').removeprefix('sha256:') or None
        download(a['browser_download_url'],archive,digest,a['size'])
        with zipfile.ZipFile(archive) as z:
            for m in z.infolist():
                if not m.is_dir():
                    target=RUNTIME/pathlib.PurePosixPath(m.filename).name
                    if not target.exists():target.write_bytes(z.read(m))
    return {'llama_cpp':'b11552','assets':[{k:a.get(k) for k in ['name','digest','size','browser_download_url']} for a in selected]}
def asr():
    pinned=json.loads((ROOT/'configs/runtime_sources.json').read_text('utf-8'))['asr'];model=pinned['repo_id']
    with fetch('https://huggingface.co/api/models/'+model+'/revision/'+pinned['revision']+'?blobs=true') as r:d=json.load(r)
    revision=d['sha'];out=MODELS/'Qwen3-ASR-0.6B'
    if revision!=pinned['revision']:raise ValueError('ASR revision mismatch')
    metadata=[x for x in d['siblings'] if not x['rfilename'].startswith('.') and not x['rfilename'].endswith(('.md','.png','.jpg'))]
    files=[x['rfilename'] for x in metadata]
    def model_file(x):
        f=x['rfilename'];sha=x.get('lfs',{}).get('sha256');size=x.get('size')
        url=f'https://modelscope.cn/models/{model}/resolve/master/{f}' if sha else f'https://huggingface.co/{model}/resolve/{revision}/{f}'
        download(url,out/f,sha,size)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(model_file,metadata))
    print(json.dumps({'ready':model,'revision':revision,'files':len(files)}),flush=True)
    return {'asr_model':model,'revision':revision,'files':files}
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(llama),pool.submit(asr)];result=[]
        for f in futures:
            try:result.append(f.result())
            except Exception as e:result.append({'status':'error','error':str(e)});print(json.dumps(result[-1]),flush=True)
    (ROOT/'reports').mkdir(exist_ok=True)
    (ROOT/'reports/runtime_preparation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
