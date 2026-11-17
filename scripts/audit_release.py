"""Read-only integrity audit of frozen inputs and actual execution/audio evidence."""
import argparse,collections,hashlib,json,sys,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from homevoice.sandbox import validate
from homevoice.speech_text import normalize,VERSION
from homevoice.runner import OFFICIAL
from homevoice.judge_schema import validate_judgment
from scripts.judge_runs import PROMPT,EVIDENCE_VERSION
def read(p):return json.loads(p.read_text('utf-8'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
ap=argparse.ArgumentParser();ap.add_argument('--require-complete',action='store_true');args=ap.parse_args()
manifest=read(ROOT/'data/manifest.json');errors=[];counts=collections.Counter();checked_audio={};cases={};pending=collections.Counter()
def check_audio(path,digest,duration=None):
    p=(ROOT/path).resolve()
    if not p.is_relative_to(ROOT.resolve()):raise ValueError('path outside release')
    if path not in checked_audio:
        if sha(p)!=digest:raise ValueError('wave hash mismatch')
        with wave.open(str(p),'rb') as w:
            frames=w.getnframes();pcm=w.readframes(frames);seconds=frames/w.getframerate()
            if len(pcm)!=frames*w.getnchannels()*w.getsampwidth():raise ValueError('invalid WAV frame declaration')
            if not .1<=seconds<=180:raise ValueError('invalid audio duration')
            if w.getnchannels()!=1:raise ValueError('expected mono')
        checked_audio[path]=(digest,seconds)
    if checked_audio[path][0]!=digest:raise ValueError('conflicting wave hash')
    if duration is not None and abs(checked_audio[path][1]-duration)>1e-5:raise ValueError('duration mismatch')
for entry in manifest['cases']:
    try:
        p=ROOT/entry['path'];c=read(p);validate(c,read(ROOT/'spec/case.schema.json'))
        if sha(p)!=entry['file_sha256']:raise ValueError('frozen case bytes changed')
        if hashlib.sha256(json.dumps(c,sort_keys=True,ensure_ascii=False).encode()).hexdigest()!=entry['canonical_sha256']:raise ValueError('canonical case hash changed')
        if c['identity']['status']!='frozen' or c['variants'][0]['modality']!='audio':raise ValueError('unfrozen/non-audio case')
        cases[entry['case_id']]=c;counts['cases']+=1
    except Exception as e:errors.append({'path':entry['path'],'error':str(e)[:700]})
for entry in manifest['audio']:
    try:
        check_audio(entry['path'],entry['sha256'],entry['duration_s']);a=read(ROOT/'runs/asr'/f'{entry["sha256"]}.json')
        if a['audio_sha256']!=entry['sha256'] or a['ground_truth_supplied'] is not False or a['model']!='Qwen/Qwen3-ASR-0.6B':raise ValueError('ASR provenance mismatch')
        counts['input_audio']+=1;counts['actual_asr']+=1
    except Exception as e:errors.append({'path':entry['path'],'error':str(e)[:700]})
byid={x['case_id']:x for x in manifest['cases']};run_schema=read(ROOT/'spec/run.schema.json')
for system in ['edge_native','qwen35_2b','qwen35_4b']:
    paths=sorted((ROOT/'runs'/system).glob('*.json'));pending[system+'_missing_run']=1000-len(paths)
    for p in paths:
        try:
            r=read(p);validate(r,run_schema);c=cases[r['case_id']]
            if r['case_sha256']!=byid[r['case_id']]['canonical_sha256']:raise ValueError('run did not use frozen case')
            if r['input_modality']!='audio' or r['normalizer_version']!=VERSION:raise ValueError('input/normalizer mismatch')
            expected={'do_sample':False,'max_tokens':256,'seed':42} if system=='edge_native' else OFFICIAL
            if r['generation']!=expected:raise ValueError('generation setting mismatch')
            if len(r['turns'])>5 or r['execution']['tool_calls']>12:raise ValueError('exceeded hard interaction bound')
            if len(r['tool_trace'])!=r['execution']['tool_calls']:raise ValueError('missing full tool trace')
            allowed_inputs={a['sha256'] for a in c['variants'][0]['audio_assets']}
            for t in r['turns']:
                if t['delivered_text'] is not None or t['input_audio_sha256'] not in allowed_inputs:raise ValueError('text delivery or unexpected audio')
                check_audio(t['input_audio'],t['input_audio_sha256'])
                if t['spoken_text']!=normalize(t['assistant_text']):raise ValueError('shared spoken normalization mismatch')
                if system=='edge_native':
                    if t['asr_text'] is not None:raise ValueError('external ASR on native system')
                else:
                    a=read(ROOT/'runs/asr'/f'{t["input_audio_sha256"]}.json')
                    if t['asr_text']!=a['text']:raise ValueError('baseline transcript not from actual ASR')
                audio=t.get('assistant_audio')
                if audio:
                    if audio['normalizer_version']!=VERSION or audio['spoken_text']!=t['spoken_text']:raise ValueError('wrong output spoken text/version')
                    if system!='edge_native' and audio.get('termination_evidence_version')!='tts_token_eos_v1':raise ValueError('missing baseline TTS termination evidence')
                    check_audio(audio['path'],audio['sha256'],audio['duration_s']);counts[system+'_audible_turns']+=1
                elif t['assistant_text'].strip():pending[system+'_missing_output_audio']+=1
            incomplete=r.get('incomplete_turn')
            if incomplete:
                if incomplete['input_audio_sha256'] not in allowed_inputs:raise ValueError('unexpected interrupted-turn audio')
                check_audio(incomplete['input_audio'],incomplete['input_audio_sha256'])
            j=r.get('audio_judge')
            if j:
                if j.get('prompt_sha256')!=hashlib.sha256(PROMPT.encode()).hexdigest() or j.get('evidence_version')!=EVIDENCE_VERSION:raise ValueError('stale judgment evidence scope')
                d=validate_judgment(j['result'],[d['id'] for d in c['evaluation']['dimensions']],[x['id'] for x in c['evaluation']['checks'] if x['method']=='semantic_judge'],[t['user_turn_index'] for t in r['turns']])
                if j['requested_model']!='qwen3.8-omni-flash' or j['temperature']!=0 or j['model_answer_text_supplied'] is not False:raise ValueError('wrong judge modality/config')
                if j['audio_sha256']!=[t['assistant_audio']['sha256'] for t in r['turns']]:raise ValueError('judge audio mismatch')
                expected_user_audio=[t['input_audio_sha256'] for t in r['turns']]+([incomplete['input_audio_sha256']] if incomplete else [])
                if j.get('user_audio_sha256')!=expected_user_audio:raise ValueError('judge user audio mismatch')
                tok=j.get('usage',{}).get('prompt_tokens_details',{}).get('audio_tokens')
                if tok==0:raise ValueError('zero actual audio input tokens')
                minimum=c['evaluation']['pass_policy']['min_applicable_dimension_score']
                expected_pass=r['execution']['status']=='completed' and all(x['passed'] for x in r['rule_checks']) and all(x['passed'] for x in d['semantic_checks']) and not d['critical_failures'] and (minimum is None or all(x['score']>=minimum for x in d['dimensions'])) and not any(t['assistant_audio'].get('hit_frame_budget',False) for t in r['turns'])
                if r['case_pass']!=expected_pass:raise ValueError('strict pass recomputation mismatch')
                counts[system+'_judged']+=1
            elif r.get('case_pass') is not None:
                if r['case_pass'] is not False or r.get('judge_status') not in ['not_applicable_no_completed_audio_turn','not_applicable_empty_response']:raise ValueError('unexplained unjudged decision')
                counts[system+'_failed_without_audio_score']+=1
            else:pending[system+'_unjudged']+=1
            counts[system+'_runs']+=1
        except Exception as e:errors.append({'path':p.relative_to(ROOT).as_posix(),'error':str(e)[:700]})
report={'status':'failed' if errors or (args.require_complete and any(pending.values())) else 'passed','scope':'complete_release' if args.require_complete else 'current_available_records','counts':dict(counts),'pending':dict(pending),'unique_waveforms_checked':len(checked_audio),'errors':errors,'frozen_manifest_sha256':sha(ROOT/'data/manifest.json')}
(ROOT/'reports/release_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8');print(json.dumps(report,ensure_ascii=False))
if report['status']!='passed':raise SystemExit(1)
