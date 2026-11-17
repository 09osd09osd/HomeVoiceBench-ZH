"""Read-only authentication/model-list probes; secrets never leave provider hosts."""
import json, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.cloud import ROOT, request, redact, load_key

def probe(provider,url):
    try:
        d=request(url,provider,attempts=1,timeout=30)
        ids=[x.get('id') for x in d.get('data',[])]
        return {'provider':provider,'status':'ok','models':[x for x in ids if any(t in x.lower() for t in ['deepseek','omni','tts'])],'model_count':len(ids)}
    except Exception as e: return {'provider':provider,'status':'error','detail':redact(e)}

with ThreadPoolExecutor(max_workers=2) as pool:
    rows=list(pool.map(lambda x:probe(*x),[('bailian','https://dashscope.aliyuncs.com/compatible-mode/v1/models'),('deepseek','https://api.deepseek.com/models')]))
(ROOT/'.local/cloud_probe.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(rows,ensure_ascii=False,indent=2))
