"""Read-only verification of the protected v0.3 files and recorded WAV hashes."""
import concurrent.futures,datetime,hashlib,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import SHARED_ROOT,CODE_ROOT
record=json.loads((SHARED_ROOT/'.local/v04-v03-preservation.json').read_text('utf-8'))
expected=dict(record['files']);audio={}
# This exact upstream documentation-only commit was fast-forwarded while the
# isolated v0.4 run continued. Keep the original snapshot immutable and disclose
# the imported README change separately; no data/result/audio exception exists.
upstream_commit='9988283ff31a234b0f0aeb17cd84e4b5a85de5c9'
upstream_readme=subprocess.check_output(['git','show',upstream_commit+':README.md'],cwd=SHARED_ROOT)
upstream_sha=hashlib.sha256(upstream_readme).hexdigest()
upstream_changes=[{'path':'README.md','original_sha256':expected['README.md'],'upstream_sha256':upstream_sha,'commit':upstream_commit,'reason':'Preserve the upstream README update without changing original benchmark data, results or audio.'}]
expected['README.md']=upstream_sha
for directory in ['data/audio','runs/tts','runs/edge_audio']:
    for p in (SHARED_ROOT/directory).glob('*.json'):
        d=json.loads(p.read_text('utf-8'));path=d.get('path');sha=d.get('sha256')
        if isinstance(path,str) and path.startswith('assets/audio/') and isinstance(sha,str) and len(sha)==64:audio[path]=sha

def add_recorded_audio(value):
    if isinstance(value,dict):
        path=value.get('path');sha=value.get('sha256')
        if isinstance(path,str) and path.startswith('assets/audio/') and isinstance(sha,str) and len(sha)==64:audio[path]=sha
        for child in value.values():add_recorded_audio(child)
    elif isinstance(value,list):
        for child in value:add_recorded_audio(child)

# Four original diagnostic WAVs record their hashes in these protected reports,
# rather than the ordinary input/output audio cache metadata.
for name in ['reports/audio_pilot.json','reports/revision/judge_controls.json','reports/revision/cloud_probe.json']:
    add_recorded_audio(json.loads((SHARED_ROOT/name).read_text('utf-8')))
def verify(item):
    name,sha=item;p=SHARED_ROOT/name
    if not p.is_file():return {'path':name,'error':'missing'}
    with p.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
    return None if actual==sha else {'path':name,'error':'changed'}
with concurrent.futures.ThreadPoolExecutor(4) as pool:errors=[e for e in pool.map(verify,{**expected,**audio}.items()) if e]
result={'status':'passed' if not errors else 'failed','checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_commit':record['source_commit'],'protected_original_files':len(expected),'protected_original_files_unchanged':len(expected)-len(upstream_changes),'documented_upstream_updates':upstream_changes,'original_audio_files_verified_against_recorded_sha256':len(audio),'errors':errors}
(CODE_ROOT/'docs/PRESERVATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(result));raise SystemExit(1 if errors else 0)
