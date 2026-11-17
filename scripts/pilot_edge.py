import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.runner import post,parse_raw
from homevoice.sandbox import ROOT,Sandbox,compact_tools
from homevoice.fixtures import fixture
from homevoice.catalog import SYSTEM_PROMPT
s=Sandbox(fixture('PILOT_AUDIO',1),{'id':'user_1','name':'小林','role':'adult_member'})
history=[{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':[{'type':'audio','audio':str(ROOT/'assets/audio/pilot/user.wav')}]}];outputs=[];spoken=[];started=time.monotonic()
for step in range(5):
    r=post('http://127.0.0.1:18931/infer',{'messages':history,'tools':compact_tools()});outputs.append(r);text,calls=parse_raw(r['raw_output']);spoken.append(text)
    history.append({'role':'assistant','content':text,'tool_calls':calls} if calls else {'role':'assistant','content':text})
    if not calls:break
    for c in calls:
        f=c['function'];response=s.call(f['name'],json.loads(f['arguments']));history.append({'role':'tool','tool_call_id':c['id'],'content':json.dumps(response,ensure_ascii=False)})
audio=post('http://127.0.0.1:18931/speak',{'text':'\n'.join(t for t in spoken if t)})
numbers=post('http://127.0.0.1:18931/speak',{'text':'编号122，温度26℃，亮度40%，时间07:30。'})
report={'record_kind':'infrastructure_pilot_not_benchmark_score','outputs':outputs,'tool_trace':s.trace,'speech':audio,'number_speech':numbers,'wall_seconds':time.monotonic()-started}
(ROOT/'reports/edge_pilot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps({'raw_outputs':[r['raw_output'] for r in outputs],'speech':audio,'number_speech':numbers,'wall_seconds':report['wall_seconds']},ensure_ascii=False))
