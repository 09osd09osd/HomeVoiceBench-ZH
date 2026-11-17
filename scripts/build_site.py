"""Generate a self-contained explanation page using real current benchmark records."""
import hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from homevoice.grading import WRITE_TOOLS
from scripts.judge_runs import PROMPT
def read(p):return json.loads(p.read_text('utf-8'))
docs=ROOT/'docs';docs.mkdir(exist_ok=True);(docs/'audio').mkdir(exist_ok=True);(docs/'examples').mkdir(exist_ok=True)
summary=read(ROOT/'reports/summary.json');rows=read(ROOT/'reports/case_overview.json');scenes=read(ROOT/'reports/scene_overview.json');sandbox=read(ROOT/'spec/sandbox.json');demos=[];rubrics={}
def local_audio(p):
    if not p or not (ROOT/p).exists():return None
    source=ROOT/p;name=source.parent.name+'-'+source.name;target=docs/'audio'/name
    # A WAV container repair can change bytes without changing file size.
    if not target.exists() or hashlib.sha256(target.read_bytes()).digest()!=hashlib.sha256(source.read_bytes()).digest():shutil.copyfile(source,target)
    return 'audio/'+name
normalization_pilot=None
if (ROOT/'reports/normalization_audio_pilot.json').exists() and (ROOT/'reports/edge_pilot.json').exists():
    check=read(ROOT/'reports/normalization_audio_pilot.json');meta=read(ROOT/'reports/edge_pilot.json')['number_speech'];source=ROOT/meta['path']
    if source.exists():
        if hashlib.sha256(source.read_bytes()).hexdigest()!=check['audio_sha256']:raise ValueError('Number pronunciation pilot audio changed')
        normalization_pilot={'raw_text':check['raw_text'],'spoken_text':check['spoken_text'],'audio':local_audio(meta['path']),'machine_check_correct':check['result']['correct'],'outside_formal_cases':True}
for cid in read(ROOT/'configs/demo_cases.json')['case_ids']:
    c=read(ROOT/'data/cases'/f'{cid}.json');rubrics[c['classification']['category']]=[{**r,'description':r['criterion']} for r in c['evaluation']['dimensions']];shutil.copyfile(ROOT/'data/cases'/f'{cid}.json',docs/'examples'/f'{cid}.json');runs={}
    for system in ['edge_native','qwen35_2b','qwen35_4b']:
        p=ROOT/'runs'/system/f'{cid}.json'
        if p.exists():runs[system]=read(p)
    d={'case_id':cid,'title':c['identity']['title'],'complete_json':f'examples/{cid}.json','turns':[]}
    for n in c['interaction']['nodes']:
        a=next(a for a in c['variants'][0]['audio_assets'] if a['node_id']==n['id']);ref=next(t for t in c['reference']['turns'] if t['node_id']==n['id']);t={'user_text':n['user_text'],'input_audio':local_audio(a['path']),'reference_text':ref['assistant_text'],'reference_calls':[x['call'] for x in ref['calls']],'systems':{}}
        for system,r in runs.items():
            actual=next((x for x in r['turns'] if x['node_id']==n['id']),None)
            if not actual:
                t['systems'][system]={'completed_turn':False,'execution_status':r['execution']['status'],'assistant_text':'该轮没有完成的口头回答。','spoken_text':'','audio':None,'tool_calls':[],'mean_score':None}
                continue
            j=r.get('audio_judge');scores=[x['score'] for x in j['result']['dimensions']] if j and j.get('prompt_sha256')==hashlib.sha256(PROMPT.encode()).hexdigest() else []
            t['systems'][system]={'completed_turn':True,'execution_status':r['execution']['status'],'assistant_text':actual['assistant_text'],'spoken_text':actual['spoken_text'],'audio':local_audio((actual.get('assistant_audio') or {}).get('path')),'tool_calls':[{'call':x['call'],'response':x['response']} for x in actual['tool_events']],'mean_score':sum(scores)/len(scores) if scores else None}
        d['turns'].append(t)
    demos.append(d)
publication=read(ROOT/'reports/publication.json') if (ROOT/'reports/publication.json').exists() else {}
data={'summary':summary,'cases':rows,'scenes':scenes,'tools':[{'name':t['name'],'description':t['description'],'write':t['name'] in WRITE_TOOLS} for t in sandbox['tools']],'rubrics':rubrics,'demos':demos,'normalization_pilot':normalization_pilot,'repository':publication.get('repository_url'),'excel':'../outputs/homevoicebench-20261117/HomeVoiceBench-ZH.xlsx'}
serialized=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
html=(ROOT/'web/index.template.html').read_text('utf-8').replace('__BENCH_DATA__',serialized);(docs/'index.html').write_text(html,'utf-8');print(json.dumps({'html':'docs/index.html','bytes':len(html.encode()),'cases':len(rows),'scenes':len(scenes),'demo_cases':len(demos)}))
