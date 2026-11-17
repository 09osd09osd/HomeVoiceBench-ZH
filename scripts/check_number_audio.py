"""Audio regression pilot, outside the 1000 benchmark cases."""
import base64,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.cloud import ROOT,chat,response_json
r=json.loads((ROOT/'reports/edge_pilot.json').read_text('utf-8'));m=r['number_speech']
content=[{'type':'text','text':'请实际听下面音频，只返回JSON，字段transcript（听到的完整原文）、correct布尔、reason。核对是否准确读出：编号一百二十二，温度二十六摄氏度，亮度百分之四十，时间七点三十分。不要根据提供的期望文本猜测，漏读、替换数字或单位要标false。'}, {'type':'input_audio','input_audio':{'data':'data:audio/wav;base64,'+base64.b64encode((ROOT/m['path']).read_bytes()).decode(),'format':'wav'}}]
out=chat('qwen3.8-omni-flash',[{'role':'user','content':content}],temperature=0,max_tokens=1000)
report={'record_kind':'normalization_audio_pilot_not_benchmark_score','audio_sha256':m['sha256'],'raw_text':m['raw_text'],'spoken_text':m['spoken_text'],'judge_model':out.get('model'),'temperature':0,'result':response_json(out),'usage':out.get('usage'),'request_id':out.get('id')}
(ROOT/'reports/normalization_audio_pilot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(report,ensure_ascii=False))
