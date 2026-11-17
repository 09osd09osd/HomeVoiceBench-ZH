"""Check official sampling/tool protocol with infrastructure-only input."""
import argparse,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from homevoice.runner import post,parse_raw,OFFICIAL
from homevoice.sandbox import Sandbox,compact_tools
from homevoice.fixtures import fixture
from homevoice.catalog import SYSTEM_PROMPT
ap=argparse.ArgumentParser();ap.add_argument('--size',choices=['2B','4B'],required=True);ap.add_argument('--port',type=int,default=18941);a=ap.parse_args()
asr=json.loads((ROOT/'reports/asr_pilot.json').read_text('utf-8'));pilot=ROOT/'assets/audio/pilot/user.wav'
import hashlib
heard=json.loads((ROOT/'runs/asr'/f'{hashlib.sha256(pilot.read_bytes()).hexdigest()}.json').read_text('utf-8'))['text']
s=Sandbox(fixture('PILOT_AUDIO',1),{'id':'user_1','name':'小林','role':'adult_member'});history=[{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':heard}];outputs=[]
for step in range(5):
    r=post(f'http://127.0.0.1:{a.port}/v1/chat/completions',{'model':f'Qwen3.5-{a.size}','messages':history,'tools':compact_tools(),'tool_choice':'auto',**OFFICIAL});outputs.append(r);m=r['choices'][0]['message'];history.append(m);calls=m.get('tool_calls') or []
    if not calls:break
    for c in calls:
        f=c['function'];response=s.call(f['name'],json.loads(f['arguments']));history.append({'role':'tool','tool_call_id':c['id'],'content':json.dumps(response,ensure_ascii=False)})
report={'record_kind':'infrastructure_pilot_not_benchmark_score','asr_text':heard,'generation':OFFICIAL,'outputs':outputs,'tool_trace':s.trace}
(ROOT/'reports'/f'qwen_{a.size}_pilot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps({'size':a.size,'calls':len(outputs),'messages':[r['choices'][0]['message'] for r in outputs]},ensure_ascii=False))
