"""Outcome diagnostics from actual records; never modifies runs or scores."""
import collections,hashlib,json,re,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.judge_runs import PROMPT
def read(p):return json.loads(p.read_text('utf-8'))
cases={p.stem:read(p) for p in (ROOT/'data/cases').glob('*.json')};systems={}
for system in ['edge_native','qwen35_2b','qwen35_4b']:
    runs=[read(p) for p in (ROOT/'runs'/system).glob('*.json')];flags=collections.Counter();rules=collections.Counter();tool_errors=collections.Counter();batches=collections.Counter();normalized=0;turns=0;numeric_turns=0;remaining_digits=0;audible=0;audio_hashes=set();audio_budget_turns=0;audio_budget_cases=set();durations=[]
    for r in runs:
        if r.get('audio_judge') and r['audio_judge'].get('prompt_sha256')!=hashlib.sha256(PROMPT.encode()).hexdigest():r['case_pass']=None
        flags.update(r['execution']['flags']);rules.update(x['check_id'] for x in r['rule_checks'] if not x['passed'])
        for e in r['tool_trace']:
            if not e['response']['ok']:tool_errors[(e['call']['tool_name'],e['response']['error']['code'])]+=1
        for t in r['turns']:
            turns+=1;normalized+=t['assistant_text']!=t['spoken_text'];numeric_turns+=bool(re.search(r'[0-9℃%]',t['assistant_text']));remaining_digits+=bool(re.search(r'[0-9]',t['spoken_text']))
            a=t.get('assistant_audio')
            if a:
                audible+=1;audio_hashes.add(a['sha256']);durations.append(a['duration_s'])
                if a.get('hit_frame_budget'):
                    audio_budget_turns+=1;audio_budget_cases.add(r['case_id'])
            for response in t['model_raw_responses']:
                if 'batch_size' in response:batches[response['batch_size']]+=1
        for response in (r.get('incomplete_turn') or {}).get('model_raw_responses',[]):
            if 'batch_size' in response:batches[response['batch_size']]+=1
    by_length=[]
    for category in ['tool','chat']:
        for n in range(1,6):
            targets=[c for c in cases.values() if c['classification']['category']==category and len(c['interaction']['nodes'])==n];ids={c['identity']['case_id'] for c in targets};actual=[r for r in runs if r['case_id'] in ids];decided=[r for r in actual if r['case_pass'] is not None];passed=sum(r['case_pass'] is True for r in decided)
            by_length.append({'category':category,'planned_user_turns':n,'planned_cases':len(targets),'run_cases':len(actual),'decided_cases':len(decided),'passed_cases':passed,'strict_pass_rate':passed/len(targets) if len(decided)==len(targets) else None})
    systems[system]={'runs':len(runs),'execution_flags':dict(flags.most_common()),'failed_rule_ids':dict(rules.most_common()),'tool_error_counts':[{'tool':k[0],'code':k[1],'count':v} for k,v in tool_errors.most_common()],'normalization':{'completed_turns':turns,'changed_spoken_text_turns':normalized,'raw_numeric_or_unit_turns':numeric_turns,'remaining_arabic_digit_turns':remaining_digits},'native_infer_batch_counts':dict(sorted(batches.items())),'by_planned_dialogue_length':by_length}
    systems[system]['audio_output']={'completed_turns_with_audio':audible,'unique_output_waveforms':len(audio_hashes),'hit_frame_budget_turns':audio_budget_turns,'cases_with_frame_budget_hit':len(audio_budget_cases),'median_duration_s':statistics.median(durations) if durations else None,'max_duration_s':max(durations) if durations else None,'scope':'actual completed audio turns; repeated cached waveforms remain represented per occurrence'}
report={'source':'actual frozen-case run files','interpretation':'Error counts describe observed behavior; no causal attribution or test-set tuning. Length groups use planned turns, not fewer completed turns after failure.','systems':systems}
(ROOT/'reports/diagnostics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8');print(json.dumps({k:{'runs':v['runs'],'normalization':v['normalization']} for k,v in systems.items()}))
