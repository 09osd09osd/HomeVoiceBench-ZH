"""Pinned Q8 backbone server; ASCII relative model paths work on Windows b11552."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import ROOT,SHARED_ROOT
ap=argparse.ArgumentParser();ap.add_argument('--size',choices=['2B','4B'],required=True);ap.add_argument('--port',type=int,default=18941);ap.add_argument('--slots',type=int,default=4);a=ap.parse_args()
exe=SHARED_ROOT/'runtime/llama-b11552/llama-server.exe';model=SHARED_ROOT/'models'/f'Qwen3.5-{a.size}-Q8_0.gguf'
args=[str(exe),'--model',model.relative_to(SHARED_ROOT).as_posix(),'--alias',f'Qwen3.5-{a.size}','--host','127.0.0.1','--port',str(a.port),'--ctx-size',str(8192*a.slots),'--parallel',str(a.slots),'--n-gpu-layers','99','--threads','8','--jinja','--no-context-shift','--chat-template-kwargs','{"enable_thinking":false}','--seed','42']
version=subprocess.check_output([str(exe),'--version'],cwd=SHARED_ROOT,text=True,encoding='utf-8',errors='replace',stderr=subprocess.STDOUT)
if 'build 11552' not in version:raise ValueError('wrong llama.cpp version')
config={'model':f'Qwen3.5-{a.size}','quantization':'Q8_0','model_sha256':hashlib.file_digest(model.open('rb'),'sha256').hexdigest(),'runtime_version':version.strip(),'context_per_slot':8192,'slots':a.slots,'context_shift':False,'command':args[1:],'shared_cuda_libraries':{p.name:hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in exe.parent.glob('*64_13.dll')}}
(ROOT/'reports'/f'qwen_{a.size}_runtime.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n','utf-8')
logs=ROOT/'logs';logs.mkdir(exist_ok=True)
with (logs/f'llama-{a.size}.log').open('w',encoding='utf-8') as log:
    p=subprocess.Popen(args,cwd=SHARED_ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
    config['server_pid']=p.pid
    (ROOT/'reports'/f'qwen_{a.size}_runtime.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps({'pid':p.pid,'port':a.port,'size':a.size,'slots':a.slots}),flush=True);raise SystemExit(p.wait())
