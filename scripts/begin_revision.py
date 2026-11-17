"""Preserve the released benchmark before an explicit protocol revision."""
import datetime, hashlib, json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / '.local/archive/v0.2.0-before-v0.3'
MARKER = DEST / 'snapshot_manifest.json'

def main():
    if MARKER.exists():
        print(json.dumps({'snapshot':'already_complete','path':str(DEST)}),flush=True)
        return
    groups=['data','spec','homevoice','scripts','reports','docs','review','tests','configs',
            'runs/edge_native','runs/qwen35_2b','runs/qwen35_4b']
    files=[p for name in groups for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [ROOT/name for name in ['README.md','.gitignore','requirements.txt','启动人工评审.cmd'] if (ROOT/name).is_file()]
    size=sum(p.stat().st_size for p in files)
    if shutil.disk_usage(ROOT).free < size*1.15:raise RuntimeError('Insufficient disk space for immutable revision snapshot')
    DEST.mkdir(parents=True,exist_ok=True);manifest=[]
    for i,p in enumerate(files,1):
        relative=p.relative_to(ROOT);target=DEST/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,target)
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise RuntimeError('Snapshot verification failed: '+relative.as_posix())
        manifest.append({'path':relative.as_posix(),'bytes':p.stat().st_size,'sha256':digest})
        if i%1000==0:print(json.dumps({'snapshot_files':i,'total':len(files)}),flush=True)
    result={'source_version':'0.2.0','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':manifest,
            'audio_policy':'Original content-addressed WAV files remain in assets/audio; no original audio will be overwritten by this revision.',
            'source_manifest_sha256':hashlib.sha256((ROOT/'data/manifest.json').read_bytes()).hexdigest()}
    MARKER.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({'snapshot':'complete','files':len(files),'bytes':size,'path':str(DEST)}),flush=True)

if __name__=='__main__':main()
