"""Resume missing author batches only, preserving already synthesized case files."""
import collections,concurrent.futures,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.generate_dataset import assignments,blueprint,process,save,ROOT,COUNTS
families={}
for d in assignments('test'):
    c=blueprint(d);families.setdefault(d['family'],[]).append(c)
values=list(families.values());jobs=[(f'test_{i//4:03d}',values[i:i+4]) for i in range(0,len(values),4)]
jobs=[job for job in jobs if not (ROOT/'data/authoring'/(job[0]+'.json')).exists()]
started=time.monotonic();errors=[]
with concurrent.futures.ThreadPoolExecutor(8) as pool:
    for f in concurrent.futures.as_completed([pool.submit(process,j) for j in jobs]):
        try:f.result()
        except Exception as e:errors.append(str(e))
save(ROOT/'reports/text_generation.json',{'requested_cases':1000,'counts':{'complete':len(list((ROOT/'data/cases').glob('*.json'))),'failed_batches':len(errors)},'errors':errors,'workers_initial':16,'workers_recovery':8,'recovery_batches':[j[0] for j in jobs],'recovery_wall_seconds':time.monotonic()-started,'recovery_reason':'One official DeepSeek request did not complete for more than 8 minutes; terminated only that author process after 174 completed batches. No generated model answer or score was retried.'})
print(json.dumps({'recovered_batches':[j[0] for j in jobs],'errors':errors}));raise SystemExit(1 if errors else 0)
