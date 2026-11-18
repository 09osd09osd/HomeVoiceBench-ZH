"""Create the isolated v0.4 source tree without modifying v0.3 evidence."""
import hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'versions/v0.4'
def main():
    if DEST.exists():raise SystemExit('v0.4 already exists; bootstrap is never destructive')
    records={}
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    for name in tracked:
        p=ROOT/name
        if name and p.is_file():records[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (ROOT/'runs').glob('*/*.json'):
        if p.parent.name in ['edge_native','qwen35_2b','qwen35_4b','asr','tts','edge_audio']:
            records[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    protected={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'files':records,'policy':'All v0.3 files remain in place; new writes are under versions/v0.4 only.'}
    (ROOT/'.local').mkdir(exist_ok=True)
    (ROOT/'.local/v04-v03-preservation.json').write_text(json.dumps(protected,ensure_ascii=False,indent=2),'utf-8')
    for directory in ['homevoice','spec','configs','review','web']:
        shutil.copytree(ROOT/directory,DEST/directory,ignore=shutil.ignore_patterns('__pycache__','preview','validation.json'))
    scripts=['edge_worker.py','launch_qwen.py','batch_speech.py','synthesize_inputs.py','judge_runs.py','judge_stream.py','run_models.py','serve_review.py','summarize.py','diagnostics.py','build_workbook.mjs','build_site.py','build_docs.py']
    (DEST/'scripts').mkdir()
    for name in scripts:shutil.copy2(ROOT/'scripts'/name,DEST/'scripts'/name)
    (DEST/'tests').mkdir();(DEST/'docs').mkdir()
    print(json.dumps({'created':str(DEST),'protected_files':len(records),'source_commit':protected['source_commit']}))
if __name__=='__main__':main()
