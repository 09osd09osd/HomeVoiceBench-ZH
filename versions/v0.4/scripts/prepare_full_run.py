"""Preserve the reviewed pilot, repair only confirmed prose defects, initialize formal data."""
import datetime,hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import CODE_ROOT
from homevoice.source_lint import naturalize,issues
from scripts.configure_v04 import initialize

pilot=CODE_ROOT/'pilot';archive=CODE_ROOT/'pilot_history/pre_full_run_protocol'
if archive.exists():raise RuntimeError('Archive already exists; inspect before retrying preparation')
shutil.copytree(pilot,archive,ignore=shutil.ignore_patterns('cache','logs','outputs','__pycache__'))
checks=[]
for folder in ['data/cases','runs/edge_native','runs/qwen35_2b','runs/qwen35_4b']:
    for p in (pilot/folder).glob('*.json'):
        a=archive/p.relative_to(pilot);sha=hashlib.sha256(p.read_bytes()).hexdigest()
        if hashlib.sha256(a.read_bytes()).hexdigest()!=sha:raise ValueError('Preservation mismatch')
        checks.append({'path':p.relative_to(pilot).as_posix(),'sha256':sha})
changed=[]
for p in (pilot/'data/cases').glob('*.json'):
    c=json.loads(p.read_text('utf-8'))
    if not any(issues(n['user_text'],c['classification']['category']) for n in c['interaction']['nodes']):continue
    cid=p.stem;changed.append(cid)
    for node in c['interaction']['nodes']:node['user_text']=naturalize(node['user_text'])
    for node in c['reference']['turns']:node['assistant_text']=naturalize(node['assistant_text'])
    for nodes in [c['design']['core_constraints'],c['evaluation']['behavior_policy']['nodes']]:
        for node in nodes:
            node['must_satisfy']=[naturalize(t) for t in node['must_satisfy']]
            if isinstance(node.get('acceptance_guidance'),str):node['acceptance_guidance']=naturalize(node['acceptance_guidance'])
    byid={n['id']:n['user_text'] for n in c['interaction']['nodes']}
    for a in c['variants'][0]['audio_assets']:
        if a['transcript_gt']!=byid[a['node_id']]:
            a.update(transcript_gt=byid[a['node_id']],status='planned',path=None,sha256=None,duration_s=None,qc_status='not_run',qc_asr_text=None)
    c['variants'][0]['status']='planned';c['provenance']['source_refs'].append('docs/FULL_RUN_POLICY.md#source-wording-repair')
    p.write_text(json.dumps(c,ensure_ascii=False,indent=2),'utf-8')
    for sid in ['edge_native','qwen35_2b','qwen35_4b']:
        target=pilot/'runs'/sid/p.name
        if not target.resolve().is_relative_to(pilot.resolve()):raise ValueError('Outside pilot')
        target.unlink() # Exact file is verified and retained in the archive above.
manifest=pilot/'data/manifest.json';manifest.rename(pilot/'data/manifest.pre_full_run.json')
report={'user_instruction':'按你修复后的标准来吧，全量运行，加快速度啊','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'prior_human_gate_superseded':True,'human_labels_claimed':False,'archive':str(archive.relative_to(CODE_ROOT)),'preserved_json_files':checks,'changed_cases':sorted(changed),'symmetric_rerun_systems':['edge_native','qwen35_2b','qwen35_4b'],'policy':'objective checks + primary audio judge + uniform transcript review; any disagreement receives one blinded fresh audio adjudication; no best-answer selection'}
(CODE_ROOT/'docs/FULL_RUN_AUTHORIZATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
initialize('test')
# Reuse only immutable, content-addressed audio and ASR/TTS caches, never model answers.
for folder in ['data/audio','assets/audio/input','runs/asr','runs/tts','assets/audio/baseline']:
    src=pilot/folder
    if src.exists():shutil.copytree(src,CODE_ROOT/'benchmark'/folder,dirs_exist_ok=True)
print(json.dumps({'archived_json':len(checks),'repaired_cases':sorted(changed),'formal_initialized':True},ensure_ascii=False))
