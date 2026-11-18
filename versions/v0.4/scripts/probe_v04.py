import base64,concurrent.futures,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.cloud import ROOT,chat,response_json,generate_audio,redact
def deepseek():
    r=chat('deepseek-v4.1-flash',[{'role':'user','content':'仅返回JSON对象，字段ok值为true。'}],temperature=0,max_tokens=40)
    return {'provider':'DeepSeek official','model':r.get('model'),'ok':response_json(r).get('ok') is True}
def audio():
    p=ROOT/'assets/audio/pilot/cloud_probe.wav';m=generate_audio('请把客厅的灯打开。',p)
    r=chat('qwen3.8-omni-flash',[{'role':'user','content':[{'type':'text','text':'听录音，只返回JSON：transcript实际听到的话。'},{'type':'input_audio','input_audio':{'data':'data:audio/wav;base64,'+base64.b64encode(p.read_bytes()).decode(),'format':'wav'}}]}],temperature=0,max_tokens=100)
    return {'tts':m['model'],'judge':r.get('model'),'ok':bool(response_json(r).get('transcript')),'usage':r.get('usage')}
out={}
with concurrent.futures.ThreadPoolExecutor(2) as pool:
    jobs={pool.submit(f):name for name,f in [('deepseek',deepseek),('audio',audio)]}
    for future in concurrent.futures.as_completed(jobs):
        try:out[jobs[future]]=future.result()
        except Exception as e:out[jobs[future]]={'ok':False,'error':redact(e)}
(ROOT/'reports/cloud_probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(out,ensure_ascii=False))
if not all(v.get('ok') for v in out.values()):raise SystemExit(1)
