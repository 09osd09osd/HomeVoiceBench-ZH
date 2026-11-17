import base64, json, sys, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.cloud import ROOT, generate_audio, chat, response_json, redact
try:
    p=ROOT/'assets/audio/pilot/user.wav'
    started=time.monotonic()
    meta=generate_audio('请把客厅的灯打开，亮度调到百分之四十。',p)
    print(json.dumps({'stage':'tts','audio':meta,'wall_seconds':time.monotonic()-started},ensure_ascii=False),flush=True)
    data='data:audio/wav;base64,'+base64.b64encode(p.read_bytes()).decode()
    result=chat('qwen3.8-omni-flash',[{'role':'user','content':[{'type':'text','text':'请听这段语音，返回JSON：transcript为听到的逐字文本，intelligibility为清晰度0到5的整数。不要猜测。'},{'type':'input_audio','input_audio':{'data':data,'format':'wav'}}]}],temperature=0,max_tokens=300)
    report={'audio':meta,'judge':response_json(result),'returned_model':result.get('model'),'usage':result.get('usage'),'temperature':0,'actual_audio_attached':True}
    (ROOT/'reports/audio_pilot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)
except Exception as e:
    print(json.dumps({'status':'failed','error':redact(e)},ensure_ascii=False));raise SystemExit(1)
