"""Explicit, reviewable v0.3 data edits; never select edits from model scores."""
import argparse, copy, hashlib, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from homevoice.authorization import compile_policy

def save(p,d):
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf-8');tmp.replace(p)

def schema():
    types_path=ROOT/'spec/types.schema.json';types=json.loads(types_path.read_text('utf-8'))
    operators=types['$defs']['Check']['properties']['operator']['enum']
    if 'read_policy_respected' not in operators:operators.append('read_policy_respected')
    save(types_path,types)
    p=ROOT/'spec/case.schema.json';d=json.loads(p.read_text('utf-8'));d['properties']['schema_version']['enum']=['0.2.0','0.3.0']
    ev=d['properties']['evaluation']['properties']
    ev['behavior_policy']={'type':'object','description':'按实际到达轮次约束查询和写操作；禁止未来授权，含语义要求。','required':['version','nodes'],'properties':{'version':{'type':'string'},'nodes':{'type':'array','minItems':1,'items':{'type':'object','required':['node_id','allowed_read_tools','allowed_writes','must_satisfy','must_not'],'properties':{'node_id':{'type':'string'},'allowed_read_tools':{'type':'array','items':{'type':'string'}},'allowed_writes':{'type':'array','items':{'type':'object'}},'must_satisfy':{'type':'array','items':{'type':'string'}},'must_not':{'type':'array','items':{'type':'string'}}}}}}}
    ev['reporting_partition']={'type':'string','enum':['standard','budget_stress'],'description':'普通任务与超出现有短答预算的长语音要求分开统计，同时保留全量成绩。'}
    ev['constraint_reference_version']={'type':'string','description':'可核验约束版本；开放式回答不匹配固定示例剧本。'}
    save(p,d)
    p=ROOT/'spec/run.schema.json';d=json.loads(p.read_text('utf-8'));d['properties']['schema_version'].pop('const',None);d['properties']['schema_version']['enum']=['0.2.0','0.3.0']
    d['properties']['revision']={'type':'object','description':'本次执行/复用来源、各协议哈希、版本和规则变更证据。'};save(p,d)
    p=ROOT/'spec/sandbox.json';d=json.loads(p.read_text('utf-8'));d['schema_version']='0.3.0'
    for t in d['tools']:
        if t['name']=='media_play':
            text='替换会话前须拥有旧会话的 media_control 权限；任一权限或新内容校验失败，旧会话保持原状。'
            if text not in t['semantic_rules']:t['semantic_rules'].append(text)
    save(p,d)

def apply_edits():
    plan=json.loads((ROOT/'data/revision/dialogue_edits.json').read_text('utf-8'));records=[]
    for cid,edits in plan['patches'].items():
        path=ROOT/'data/cases'/f'{cid}.json';c=json.loads(path.read_text('utf-8'))
        for node in c['interaction']['nodes']:
            if node['id'] not in edits:continue
            old=node['user_text'];new=edits[node['id']]
            if old==new:continue
            records.append({'case_id':cid,'node_id':node['id'],'old':old,'new':new,'reason':'Repair missing user antecedent or dependence on a freely chosen assistant answer.'})
            node['user_text']=new
            a=next(a for a in c['variants'][0]['audio_assets'] if a['node_id']==node['id'])
            a.update(status='planned',path=None,sha256=None,duration_s=None,sample_rate_hz=None,channels=None,codec=None,transcript_gt=new,qc_status='not_run',qc_asr_text=None,processing=[])
        c['variants'][0]['status']='planned';c['identity'].update(case_version='2.0',status='reviewed');save(path,c)
    # Explicit numeric-game truth; reference-only changes preserve the actual input WAVs.
    for i in range(1,6):
        p=ROOT/'data/cases'/f'C16_{i:03}.json';c=json.loads(p.read_text('utf-8'))
        texts=['先报一个数：一。保持每次一个数、跳过七及七的倍数的规则。','确认新增禁用含七数字；依实际已发生的报数继续，不能假定用户报过未说的数字。','接受从五重新开始，助手先报五；保留最新禁用规则。','复述最新起点是五；跳过七的倍数及含七的数字，每次只报一个数。','简短总结最终有效规则，不以最初起点一代替已更正的五。']
        for t,text in zip(c['reference']['turns'],texts):t['assistant_text']=text
        save(p,c)
    p=ROOT/'data/cases/C16_016.json';c=json.loads(p.read_text('utf-8'));c['reference']['turns'][0]['assistant_text']='接受不重复、每人最多接三次和出错重来的规则，请用户先给出第一个词，不替用户虚构已报词。';save(p,c)
    for i in range(11,16):
        p=ROOT/'data/cases'/f'T30_{i:03}.json';c=json.loads(p.read_text('utf-8'));c['reference']['turns'][0]['assistant_text']='开灯并调至百分之六十的任务已接受，目前工具返回处理中；仅在后续真实任务或设备状态证据确认后才声称已经完成。';save(p,c)
    target=ROOT/'reports/revision/dialogue_changes.json'
    if records:
        previous=json.loads(target.read_text('utf-8')).get('changed_nodes',[]) if target.exists() else []
        save(target,{'changed_cases':sorted(plan['patches']),'changed_nodes':previous+records,'selection_basis':'source-only input consistency and chat intent alignment; all three systems rerun for each changed case'})
    print(json.dumps({'dialogue_changed_cases':len(plan['patches']),'newly_changed_nodes':len(records)}),flush=True)

def policies(audit_dir):
    plan=json.loads((ROOT/'data/revision/dialogue_edits.json').read_text('utf-8'));audits={}
    overrides=json.loads((ROOT/'data/revision/constraint_overrides.json').read_text('utf-8'))
    for p in audit_dir.glob('*.json'):
        for c in json.loads(p.read_text('utf-8'))['cases']:audits[c['case_id']]=c
    count=0
    for p in sorted((ROOT/'data/cases').glob('*.json')):
        c=json.loads(p.read_text('utf-8'));cid=p.stem;chat=c['classification']['category']=='chat'
        if chat and cid not in audits:raise ValueError('Missing final source constraints: '+cid)
        constraints=copy.deepcopy(audits[cid]['nodes']) if chat else None
        for n in constraints or []:
            edits=overrides['nodes'].get(cid,{}).get(n['node_id'],{})
            for key in ('must_satisfy','must_not'):
                if 'replace_'+key in edits:n[key]=edits['replace_'+key]
                n[key]=[s for s in n[key] if not any(re.search(p,s) for p in edits.get('remove_'+key+'_patterns',[]))]+edits.get('add_'+key,[])
            if cid.startswith('C15_'):n['must_satisfy'].append(overrides['general']['riddle_guess'])
        c['schema_version']='0.3.0';c['identity'].update(case_version='2.0',status='reviewed')
        c['evaluation'].update(rubric_version='home_audio_v0.3',constraint_reference_version='source_constraints_v0.3',reporting_partition='budget_stress' if cid in plan['budget_stress'] else 'standard',behavior_policy=compile_policy(c,constraints))
        for check in c['evaluation']['checks']:
            if check['id']=='NO_TOOLS':check.update(id='READ_BOUNDARY',operator='read_policy_respected',expected=True,description='遵守当前及此前用户明确提出的查询限制；合理只读查询不自动失败。')
            if check['id']=='NO_EXTRA':check['description']='每一实际轮次只尝试当前授权的对象、字段与值，不得提前使用未来授权；误改再恢复仍失败。'
            if check['id']=='CONTENT':check['description']='根据实际用户语音与实际对话满足可核验约束；开放题允许其他合理创作，不将示例细节或用户猜测视为唯一答案。'
        if chat:
            for t,node in zip(c['reference']['turns'],constraints):
                t['assistant_text']='预期要点：'+'；'.join(node['must_satisfy'])+('。避免：'+'；'.join(node['must_not']) if node['must_not'] else '')+'。'
        c['reference']['acceptable_alternatives']=['依据用户实际要求与真实历史评价，允许不同措辞、合法查询和等价合法工具路径。','开放创作中的人物、词语、谜底以该模型实际给出的内容为准；用户猜测不自动成为正确答案。']
        c['provenance']['source_refs']=list(dict.fromkeys(c['provenance']['source_refs']+['data/revision/dialogue_edits.json']))
        c['quality']['known_limitations']=list(dict.fromkeys(c['quality']['known_limitations']+['v0.3 进行规则修订、Codex源数据复核及DeepSeek官方API机器审题；不等同人工校准。']))
        save(p,c);count+=1
    print(json.dumps({'migrated_cases':count,'version':'0.3.0'}),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['schema','edits','policies']);ap.add_argument('--audit-dir',type=Path,default=ROOT/'data/revision/audit_final');args=ap.parse_args()
    if args.phase=='schema':schema()
    elif args.phase=='edits':apply_edits()
    else:policies(args.audit_dir)
