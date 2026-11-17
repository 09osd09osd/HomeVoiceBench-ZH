"""Make only fully verified cases available to the model runner during generation."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.cloud import ROOT
from homevoice.speech_text import VERSION
VOICE=['成年女性，标准普通话，自然交谈','成年男性，标准普通话，语气温和','成年女性，标准普通话，语速略慢','成年男性，标准普通话，自然轻快']
def sync():
    ready=0;changed=0
    for path in sorted((ROOT/'data/cases').glob('*.json')):
        c=json.loads(path.read_text('utf-8'));voice=VOICE[(int(c['identity']['case_id'][-3:])-1)//5];dirty=False
        for a in c['variants'][0]['audio_assets']:
            key=hashlib.sha256(json.dumps({'text':a['transcript_gt'],'voice':voice,'tone':a['tone'],'seed':42,'normalizer':VERSION,'model':'qwen-audio-3.1-tts-next'},ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:32]
            p=ROOT/'data/audio'/f'{key}.json'
            if not p.exists():continue
            m=json.loads(p.read_text('utf-8'))
            if m['status']!='verified':continue
            if a['status']=='verified' and a['sha256']==m['sha256']:continue
            a.update(status='verified',path=m['path'],sha256=m['sha256'],duration_s=m['duration_seconds'],sample_rate_hz=m['sample_rate'],channels=m['channels'],codec=m['codec'],voice_id=m['voice_description'],seed=m['seed'],qc_status='machine_pass',qc_asr_text=m['qc']['result']['transcript'],processing=['Shared spoken normalization: '+VERSION,'Qwen3.8-Omni-Flash listened to actual WAV for QC; temperature=0']);dirty=True
        available=all(a['status']=='verified' for a in c['variants'][0]['audio_assets']);status='ready' if available else 'planned'
        if c['variants'][0]['status']!=status:c['variants'][0]['status']=status;dirty=True
        ready+=available
        if dirty:
            tmp=path.with_suffix('.sync.tmp');tmp.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n','utf-8');tmp.replace(path);changed+=1
    return {'ready_cases':ready,'changed_cases':changed}
if __name__=='__main__':print(json.dumps(sync()))
