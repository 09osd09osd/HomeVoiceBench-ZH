"""Technical acceptance never uses a desired model pass-rate threshold."""
import collections,datetime,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import ROOT
from scripts.judge_runs import judgment_current
from homevoice.sandbox import validate
from scripts.review_semantics import current as review_current
from homevoice.source_lint import issues as source_issues
from scripts.adjudicate_audio import current as adjudication_current

def check():
    errors=[];manifest=json.loads((ROOT/'data/manifest.json').read_text('utf-8'));cases={};audio={};counts={};schema=json.loads((ROOT/'spec/run.schema.json').read_text('utf-8'))
    def require(condition,reason):
        if not condition:errors.append(reason)
    for entry in manifest['cases']:
        p=ROOT/entry['path'];require(hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256'],'input changed: '+p.stem)
        c=json.loads(p.read_text('utf-8'));cases[p.stem]=c
        require(not any(source_issues(n['user_text'],c['classification']['category']) for n in c['interaction']['nodes']),'spoken source identifiers: '+p.stem)
        require(c['variants'][0]['status']=='ready','input not ready: '+p.stem)
        for a in c['variants'][0]['audio_assets']:audio[a['path']]=a['sha256']
    expected=100 if ROOT.name=='pilot' else 1000;require(len(cases)==expected,'case count')
    require(sum(c['design']['grouped'] for c in cases.values())==expected*.4,'40% grouped')
    for system in ['edge_native','qwen35_2b','qwen35_4b']:
        paths=sorted((ROOT/'runs'/system).glob('*.json'));require({p.stem for p in paths}==set(cases),'system case coverage: '+system)
        rr=[]
        for p in paths:
            r=json.loads(p.read_text('utf-8'));rr.append(r);c=cases[p.stem];label=system+'/'+p.stem
            try:validate(r,schema)
            except Exception as e:errors.append(label+' run schema: '+str(e))
            require(r['input_modality']=='audio',label+' input modality')
            require(r['generation']['temperature']==0,label+' temperature')
            if system=='edge_native':require(r['generation']['do_sample'] is False,label+' sampling')
            else:require(r['generation']['top_k']==1 and r['generation']['top_p']==1 and r['generation']['repeat_penalty']==1,label+' greedy config')
            require(type(r.get('case_pass')) is bool,label+' unresolved decision')
            require(not (r['execution'].get('failure') or {}).get('infra_candidate'),label+' infrastructure error requires resolution')
            require(not r.get('audio_fact_review_required'),label+' audio facts require review')
            if r.get('audio_judge'):
                require(judgment_current(c,r),label+' outdated judge evidence')
                require(review_current(c,r),label+' missing/outdated semantic consistency review')
                if (r.get('semantic_review') or {}).get('decision_status')=='disputed':require(adjudication_current(c,r),label+' missing/outdated final audio adjudication')
            else:require(r.get('case_pass') is False and r.get('judge_status','').startswith('not_applicable'),label+' missing judge')
            for t in r['turns']:
                a=t.get('assistant_audio')
                if a:audio[a['path']]=a['sha256']
        counts[system]={'runs':len(rr),'passed':sum(r.get('case_pass') is True for r in rr),'execution_failed':sum(r['execution']['status']=='failed' for r in rr)}
    for path,sha in audio.items():
        p=ROOT/path;require(p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==sha,'audio missing/changed: '+path)
    calibration=ROOT/'reports/semantic_regression.json' if ROOT.name=='pilot' else ROOT.parent/'pilot/reports/semantic_regression.json'
    from homevoice.paths import CODE_ROOT
    authorization=CODE_ROOT/'docs/FULL_RUN_AUTHORIZATION.json'
    policy=ROOT/'spec/scoring_policy.json'
    require(authorization.exists() and json.loads(authorization.read_text('utf-8')).get('prior_human_gate_superseded') is True,'full-run scoring authorization missing')
    require(policy.exists(),'frozen scoring policy missing')
    if policy.exists():
        from scripts.judge_runs import PROMPT as primary_prompt
        from scripts.review_semantics import PROMPT as review_prompt
        from scripts.adjudicate_audio import PROMPT as adjudication_prompt
        frozen=json.loads(policy.read_text('utf-8'))
        for key,prompt in [('primary',primary_prompt),('semantic_review',review_prompt),('adjudication',adjudication_prompt)]:require(frozen[key+'_prompt_sha256']==hashlib.sha256(prompt.encode()).hexdigest(),'scoring prompt changed: '+key)
        require(manifest.get('scoring_policy_sha256')==hashlib.sha256(policy.read_bytes()).hexdigest(),'scoring policy differs from frozen input manifest')
    diagnostic_status=json.loads(calibration.read_text('utf-8')).get('status') if calibration.exists() else 'not_available'
    result={'version':'0.4.0','split':manifest['split'],'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'passed' if not errors else 'needs_attention','checks':['frozen case SHA256','exact three-system coverage','audio input and output SHA256','greedy parameters','current audio-judge evidence','uniform semantic consistency review','no unresolved infrastructure errors','numeric audio disagreement review','separate task vs quality decisions'],'not_claimed':['independent human rating calibration','target pass rate attained','real-time interactive latency'],'cases':len(cases),'unique_audio_files_verified':len(audio),'systems':counts,'errors':errors}
    result['scoring_policy']='objective_rules_plus_audio_judge_with_blinded_audio_adjudication';result['human_calibration_performed']=False;result['diagnostic_counterexample_status']=diagnostic_status
    result['warnings']=['No independent human calibration; final judgments remain same-model automated ratings.']
    if diagnostic_status!='passed':result['warnings'].append('Earlier agent-reviewed counterexamples were not all matched. They are diagnostics, not independent human gold or a claim of calibrated judge accuracy.')
    (ROOT/'reports/acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(result,ensure_ascii=False));return not errors
if __name__=='__main__':raise SystemExit(0 if check() else 1)
