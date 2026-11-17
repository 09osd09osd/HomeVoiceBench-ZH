"""Batch/serial equivalence probe outside the frozen benchmark."""
import concurrent.futures,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from homevoice.runner import post
from homevoice.catalog import SYSTEM_PROMPT
from homevoice.sandbox import compact_tools
messages=[{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':[{'type':'audio','audio':str(ROOT/'assets/audio/pilot/user.wav')}]}]
payloads=[{'messages':messages+([{'role':'assistant','content':'好的，我会先核对设备。'},messages[-1]]*i),'tools':compact_tools()} for i in range(4)];url='http://127.0.0.1:18931/infer';one=[post(url,p) for p in payloads];start=time.monotonic()
with concurrent.futures.ThreadPoolExecutor(4) as pool:many=list(pool.map(lambda p:post(url,p),payloads))
report={'record_kind':'infrastructure_batch_probe_not_benchmark_score','serial':one,'concurrent':many,'concurrent_wall_seconds':time.monotonic()-start,'identical_raw_outputs':all(x['raw_output']==y['raw_output'] for x,y in zip(many,one))}
(ROOT/'reports/edge_batch_pilot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps({'same_output':report['identical_raw_outputs'],'batches':[x['batch_size'] for x in many],'wall_seconds':report['concurrent_wall_seconds'],'serial_seconds':sum(x['batch_wall_seconds'] for x in one)},ensure_ascii=False))
if not report['identical_raw_outputs']:raise SystemExit('Batch equivalence check failed')
