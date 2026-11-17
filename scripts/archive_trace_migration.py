import datetime,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];archive=ROOT/'runs/infra_attempts/pre_complete_trace';archive.mkdir(parents=True,exist_ok=True);counts={}
for system in ['edge_native','qwen35_2b']:
    source=ROOT/'runs'/system;target=archive/system
    if not source.resolve().is_relative_to(ROOT.resolve()) or not target.resolve().is_relative_to(ROOT.resolve()):raise ValueError('path outside project')
    if target.exists():raise ValueError('archive already exists')
    counts[system]=len(list(source.glob('*.json')));shutil.move(str(source),str(target))
report={'reason':'Uniform restart of both active run sets after adding lossless failure trace capture. Original executions are retained. Prompts, input audio, model sampling and pass rules unchanged. No selection by model score.','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archived':counts}
(archive/'reason.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(report))
