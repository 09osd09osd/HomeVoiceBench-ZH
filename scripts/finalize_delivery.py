"""Rebuild all delivery files only after full actual evaluation is available."""
import json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
retry_plan=ROOT/'reports/pending_infra_retry.json'
if retry_plan.exists() and json.loads(retry_plan.read_text('utf-8')).get('status')!='completed':raise ValueError('Reviewed infrastructure retry is still pending; finish it before final delivery')
def run(args):subprocess.run(args,cwd=ROOT,check=True)
for name in ['summarize.py','diagnostics.py']:
    run([sys.executable,'-X','utf8','scripts/'+name])
if json.loads((ROOT/'reports/summary.json').read_text('utf-8'))['evaluation_status']!='complete':raise ValueError('Evaluation is not complete')
run([sys.executable,'-X','utf8','scripts/audit_release.py','--require-complete'])
run([sys.executable,'-X','utf8','scripts/build_docs.py'])
run([os.getenv('HOMEVOICE_NODE','node'),'--max-old-space-size=4096','scripts/build_workbook.mjs'])
run([sys.executable,'-X','utf8','scripts/build_site.py'])
run([sys.executable,'-X','utf8','scripts/package_release.py','--part','evaluation'])
print('Local delivery rebuilt from complete audited evaluation. Review previews, then publish using existing GitHub authentication.')
