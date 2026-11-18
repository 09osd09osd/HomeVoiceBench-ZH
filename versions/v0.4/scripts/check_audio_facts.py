import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import ROOT
from homevoice.audio_facts import evaluate
from scripts.adjudicate_audio import current as adjudication_current
transcripts={p.stem:json.loads(p.read_text('utf-8'))['text'] for p in (ROOT/'runs/output_asr').glob('*.json')};rows=[]
for system in ['edge_native','qwen35_2b','qwen35_4b']:
    for p in sorted((ROOT/'runs'/system).glob('*.json')):
        r=json.loads(p.read_text('utf-8'));c=json.loads((ROOT/'data/cases'/p.name).read_text('utf-8'));facts=evaluate(c,r,transcripts)
        r['objective_audio_checks']=facts
        r['audio_fact_review_required']=any(x['status'] in ['needs_review','pending_transcription'] or x['status']=='value_missing_in_both' and r.get('case_pass') for x in facts)
        if adjudication_current(c,r):
            decisions={x['check_id']:x for x in r['audio_adjudication']['result']['numeric_checks']}
            for f in facts:
                if f['check_id'] in decisions:f['fresh_audio_verification']=decisions[f['check_id']]
            r['audio_fact_review_required']=False
        p.write_text(json.dumps(r,ensure_ascii=False,indent=2),'utf-8')
        for f in facts:rows.append({'system_id':system,'case_id':p.stem,**f,'overall_pass':r.get('case_pass'),'requires_review':r['audio_fact_review_required']})
(ROOT/'reports/objective_audio_checks.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'checks':len(rows),'review_rows':sum(x['requires_review'] for x in rows)},ensure_ascii=False))
