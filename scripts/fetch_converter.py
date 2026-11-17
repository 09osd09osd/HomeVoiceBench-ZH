"""Fetch pinned upstream Python conversion files in parallel, without a full source archive."""
import concurrent.futures,hashlib,json,time,urllib.error,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];target=ROOT/'runtime/llama-b11552-source'
manifest=json.loads((ROOT/'configs/pinned_converter_files.json').read_text('utf-8'))
expected={x['path']:x['sha256'] for x in manifest['files'] if 'sha256' in x};paths=list(expected)
def get(path):
    out=target/path
    if out.exists() and hashlib.sha256(out.read_bytes()).hexdigest()==expected[path]:return {'path':path,'sha256':expected[path]}
    for attempt in range(4):
        try:
            req=urllib.request.Request('https://raw.githubusercontent.com/ggml-org/llama.cpp/23b0202a1/'+path,headers={'User-Agent':'HomeVoiceBench-ZH'})
            with urllib.request.urlopen(req,timeout=40) as r:data=r.read()
            digest=hashlib.sha256(data).hexdigest()
            if digest!=expected[path]:raise ValueError('pinned source checksum mismatch: '+path)
            out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);return {'path':path,'sha256':digest}
        except urllib.error.HTTPError as e:
            if attempt==3:raise
        except Exception:
            if attempt==3:raise
        time.sleep(2**attempt)
with concurrent.futures.ThreadPoolExecutor(16) as pool:records=list(pool.map(get,paths))
(target/'PINNED_SOURCE.json').write_bytes((ROOT/'configs/pinned_converter_files.json').read_bytes());print(json.dumps({'pinned_files':len(records),'revision':manifest['revision']}))
