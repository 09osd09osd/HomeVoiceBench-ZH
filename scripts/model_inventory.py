"""Record actual model/config hashes without publishing local paths or weights."""
import concurrent.futures,hashlib,json,os,platform,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from homevoice.paths import model_path
def hashed(p):
    with p.open('rb') as f:d=hashlib.file_digest(f,'sha256').hexdigest()
    return {'name':p.name,'bytes':p.stat().st_size,'sha256':d}
def model_record(key):
    directory=model_path(key);files=sorted(p for p in directory.iterdir() if p.is_file() and p.suffix in ['.safetensors','.json','.py','.txt'])
    return key,{'directory_name':directory.name,'files':[hashed(p) for p in files]}
started=time.monotonic()
with concurrent.futures.ThreadPoolExecutor(2) as pool:models=dict(pool.map(model_record,['edge_model','asr_model','tts_model','source_2b','source_4b']))
ff=model_path('ffmpeg');version=subprocess.check_output([str(ff),'-version'],text=True,encoding='utf-8',errors='replace').splitlines()[0]
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'],text=True).strip()
report={'system':'Windows' if os.name=='nt' else platform.system(),'python':sys.version.split()[0],'logical_cpu_count':os.cpu_count(),'gpu':gpu,'models':models,'ffmpeg':{**hashed(ff),'version':version},'hashing_seconds':time.monotonic()-started,'weights_included_in_repository':False}
(ROOT/'reports/model_inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8');print(json.dumps({'models':len(models),'files_hashed':sum(len(m['files']) for m in models.values()),'weight_files':sum(p['name'].endswith('.safetensors') for m in models.values() for p in m['files']),'seconds':report['hashing_seconds']}))
