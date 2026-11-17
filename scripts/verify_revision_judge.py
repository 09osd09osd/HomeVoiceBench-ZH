"""Small audible positive/negative controls, separate from benchmark/model scores."""
import concurrent.futures,copy,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from homevoice.cloud import generate_audio,chat,response_json
from homevoice.judge_schema import validate_judgment
from scripts.judge_runs import PROMPT,observed_context,audio_part
from scripts.migrate_revision_dataset import save

def work(label,answer,expected):
    case=json.loads((ROOT/'data/cases/C16_001.json').read_text('utf-8'));asset=case['variants'][0]['audio_assets'][0]
    target=ROOT/'assets/audio/revision_controls'/f'count_start_{label}.wav'
    meta=generate_audio(answer,target,seed=42)
    run={'turns':[{'node_id':'U1','user_turn_index':1,'tool_events':[],'assistant_audio':meta}],
         'incomplete_turn':None,'tool_trace':[],'execution':{'status':'completed'},'rule_checks':[]}
    content=[{'type':'text','text':json.dumps(observed_context(case,run),ensure_ascii=False)},
             {'type':'text','text':'第一轮，用户语音：'},audio_part(asset['path']),
             {'type':'text','text':'第一轮，助手实际回答语音：'},audio_part(meta['path'])]
    response=chat('qwen3.8-omni-flash',[{'role':'system','content':PROMPT},{'role':'user','content':content}],temperature=0,max_tokens=6000)
    result=validate_judgment(response_json(response),{d['id'] for d in case['evaluation']['dimensions']},{c['id'] for c in case['evaluation']['checks'] if c['method']=='semantic_judge'},[1])
    content_check=next(c for c in result['semantic_checks'] if c['check_id']=='CONTENT')
    return {'label':label,'source_case':'C16_001','fixture_kind':'authored_protocol_control_not_model_output','spoken_answer':answer,
            'expected_content_pass':expected,'observed_content_pass':content_check['passed'],'control_passed':content_check['passed']==expected,
            'audio':meta,'response':response,'judge_result':result,'prompt_sha256':hashlib.sha256(PROMPT.encode()).hexdigest()}

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        rows=list(pool.map(lambda x:work(*x),[('correct_one','一。',True),('wrong_two','二。',False)]))
    report={'purpose':'Check the corrected initial-number rule using actual audio, not textual judge substitution. Two controls do not establish general judge accuracy or human calibration.',
            'controls':rows,'passed':all(r['control_passed'] for r in rows)}
    save(ROOT/'reports/revision/judge_controls.json',report)
    print(json.dumps({'passed':report['passed'],'controls':[{k:r[k] for k in ['label','expected_content_pass','observed_content_pass','control_passed']} for r in rows]}),flush=True)
    if not report['passed']:raise SystemExit(1)
