import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import ROOT
from homevoice.source_lint import issues
rows=[]
for p in sorted((ROOT/'data/cases').glob('*.json')):
    c=json.loads(p.read_text('utf-8'))
    for n in c['interaction']['nodes']:
        hits=issues(n['user_text'],c['classification']['category'])
        if hits:rows.append({'case_id':p.stem,'node_id':n['id'],'text':n['user_text'],'residual_terms':hits})
report={'status':'needs_attention' if rows else 'passed','affected_cases':len({r['case_id'] for r in rows}),'affected_turns':len(rows),'scope':'Tool-field identifiers leaked into supposedly natural household user wording; frozen inputs are not silently edited.','rows':rows}
(ROOT/'reports/spoken_source_lint.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps({k:v for k,v in report.items() if k!='rows'}));raise SystemExit(1 if rows else 0)
