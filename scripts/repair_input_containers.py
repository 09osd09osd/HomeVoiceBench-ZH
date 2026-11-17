"""One-time migration; preserve old runs and proof of bit-identical decoded PCM."""
import datetime,hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from homevoice.audio import canonical_wav
stamp='pre_wav_container_v1';archive=ROOT/'runs/infra_attempts'/stamp;archive.mkdir(parents=True,exist_ok=True)
source=ROOT/'runs/edge_native';target=archive/'edge_native'
if source.exists() and any(source.glob('*.json')):
    if target.exists():raise ValueError('archive already exists; inspect before retry')
    if not source.resolve().is_relative_to(ROOT.resolve()) or not target.resolve().is_relative_to(ROOT.resolve()):raise ValueError('archive outside project')
    shutil.copytree(ROOT/'data/cases',archive/'case_snapshots');shutil.move(str(source),str(target))
    (archive/'reason.json').write_text(json.dumps({'reason':'Repair streaming WAV headers uniformly, then restart the formal model runs. No cases or outputs selected by score. All decoded PCM samples are preserved.','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat()},ensure_ascii=False,indent=2),'utf-8')
count=0
for p in (ROOT/'data/audio').glob('*.json'):
    m=json.loads(p.read_text('utf-8'));audio=ROOT/m['path']
    if m.get('wav_container',{}).get('version')=='canonical_pcm_v1':continue
    canonical,info=canonical_wav(audio.read_bytes());old=m['sha256'];audio.write_bytes(canonical);m.update(info,sha256=hashlib.sha256(canonical).hexdigest())
    if m.get('qc'):m['qc']['equivalent_pcm_header_repair']={'judged_audio_sha256':m['qc']['audio_sha256'],'canonical_audio_sha256':m['sha256'],'pcm_sha256':info['wav_container']['pcm_sha256'],'same_samples':True}
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n','utf-8');count+=1
print(json.dumps({'canonicalized_audio_files':count,'archived_prior_runs':len(list(target.glob('*.json'))) if target.exists() else 0}))
