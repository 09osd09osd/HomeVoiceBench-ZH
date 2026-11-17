"""Freeze machine-validated cases; 'frozen' does not imply human review."""
import datetime,hashlib,json,sys,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from homevoice.sandbox import validate
schema=json.loads((ROOT/'spec/case.schema.json').read_text('utf-8'));cases=[];assets={}
for p in sorted((ROOT/'data/cases').glob('*.json')):
    c=json.loads(p.read_text('utf-8'));validate(c,schema)
    if c['variants'][0]['status']!='ready':raise ValueError('Input audio pending: '+p.stem)
    for a in c['variants'][0]['audio_assets']:
        if a['status']!='verified':raise ValueError('Audio not verified')
        audio=ROOT/a['path'];digest=hashlib.sha256(audio.read_bytes()).hexdigest()
        if digest!=a['sha256']:raise ValueError('Audio hash mismatch')
        with wave.open(str(audio),'rb') as w:
            actual=w.getnframes()/w.getframerate()
            if not .1<=actual<=120 or abs(actual-a['duration_s'])>1e-6:raise ValueError('WAV duration mismatch')
        assets[digest]={'path':a['path'],'sha256':digest,'duration_s':a['duration_s']}
    c['identity']['status']='frozen';cases.append((p,c))
if len(cases)!=1000:raise ValueError('Expected all 1000 cases')
manifest={'version':'0.2.0','frozen_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'meaning':'Immutable machine-validated release; human review not performed. No test-set tuning.','cases':[],'audio':list(assets.values())}
for p,c in cases:
    p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n','utf-8');manifest['cases'].append({'case_id':p.stem,'path':p.relative_to(ROOT).as_posix(),'file_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'canonical_sha256':hashlib.sha256(json.dumps(c,ensure_ascii=False,sort_keys=True).encode()).hexdigest()})
(ROOT/'data/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf-8');print(json.dumps({'frozen_cases':len(cases),'unique_audio':len(assets),'audio_hours':sum(a['duration_s'] for a in assets.values())/3600}))
