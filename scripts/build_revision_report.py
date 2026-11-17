"""Explain score changes without conflating new inputs with rule-only effects."""
import collections,copy,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from homevoice.semantics import equivalent
from homevoice.authorization import READ_TOOLS
from scripts.migrate_revision_dataset import save
OLD=ROOT/'.local/archive/v0.2.0-before-v0.3'
SYSTEMS=['edge_native','qwen35_2b','qwen35_4b']
def read(p):return json.loads(p.read_text('utf-8'))

def passes_with_rules(run,rules):
    j=run.get('audio_judge')
    if not j:return False
    d=j['result'];minimum=3 if run['case_id'].startswith('C') else None
    return run['execution']['status']=='completed' and all(x['passed'] for x in rules) and all(x['passed'] for x in d['semantic_checks']) and not d['critical_failures'] and (minimum is None or all(x['score']>=minimum for x in d['dimensions'])) and not any((t.get('assistant_audio') or {}).get('hit_frame_budget',False) for t in run['turns'])

def main():
    plan=read(ROOT/'reports/revision/replay_plan.json');rows=[];audits={};oldcompact=[]
    for system in SYSTEMS:
        time_cases=[];time_checks=0;time_flips=[];read_only=[];overall=collections.Counter()
        for p in sorted((OLD/'runs'/system).glob('*.json')):
            old=read(p);cid=p.stem;case=read(OLD/'data/cases'/p.name);old_rules=old['rule_checks'];time_rules=copy.deepcopy(old_rules);modified=[]
            definitions={c['id']:c for c in case['evaluation']['checks']}
            for r in time_rules:
                definition=definitions[r['check_id']]
                if definition['operator']=='state_matches' and not r['passed'] and isinstance(r['observed'],dict) and equivalent(r['observed'],definition['expected']):
                    r['passed']=True;modified.append(r['check_id'])
            if modified:
                time_cases.append(cid);time_checks+=len(modified)
                if not old['case_pass'] and passes_with_rules(old,time_rules):time_flips.append(cid)
            if cid.startswith('C') and old['tool_trace'] and all(e['call']['tool_name'] in READ_TOOLS for e in old['tool_trace']):
                revised=[{**r,'passed':True} if r['check_id']=='NO_TOOLS' else r for r in old_rules]
                if not old['case_pass'] and passes_with_rules(old,revised):read_only.append(cid)
            target=ROOT/'runs'/system/p.name;new=read(target) if target.exists() else None
            current_pass=new.get('case_pass') if new else None
            if current_pass is not None:
                overall['decided']+=1;overall['old_passed']+=old['case_pass'] is True;overall['new_passed']+=current_pass is True
                overall['fail_to_pass']+=not old['case_pass'] and current_pass
                overall['pass_to_fail']+=old['case_pass'] and not current_pass
            oldcompact.append({'system_id':system,'case_id':cid,'case_pass':old['case_pass'],'task_achieved':old.get('task_achieved'),
                               'rule_checks':old_rules,'dimensions':old.get('audio_judge',{}).get('result',{}).get('dimensions') if old.get('audio_judge') else None,
                               'source_run_file_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
            rows.append({'system_id':system,'case_id':cid,'old_pass':old['case_pass'],'new_pass':current_pass,
                         'execution_origin':new.get('revision',{}).get('execution_origin') if new else 'pending',
                         'rerun_reasons':plan['rerun_cases'].get(cid,[]),'old_failed_rules':[r['check_id'] for r in old_rules if not r['passed']],
                         'new_failed_rules':[r['check_id'] for r in new['rule_checks'] if not r['passed']] if new else None,
                         'causal_comparison_limit':'input_or_sandbox_changed' if cid in plan['rerun_cases'] else 'same_model_output_new_rules_and_judge',
                         'time_equivalent_checks_on_original':modified,'rule_only_read_allowance_flips_on_original':cid in read_only})
        audits[system]={'time_equivalence_affected_cases':time_cases,'time_equivalence_affected_checks':time_checks,'time_only_counterfactual_fail_to_pass':time_flips,
                        'read_only_no_tools_counterfactual_fail_to_pass':read_only,'current_comparison':dict(overall)}
    result={'version':'0.3.0','complete':all(a['current_comparison']['decided']==1000 for a in audits.values()),
            'attribution_warning':'Counterfactual rule-only flips keep v0.2 audio judgments unchanged; they are diagnostic, not v0.3 official scores. Input/sandbox changed cases are different test conditions, not a causal model improvement.',
            'systems':audits,'rows':rows}
    save(ROOT/'reports/revision/score_changes.json',result);save(ROOT/'reports/revision/v0.2_final_scores.json',oldcompact)
    lines=['# v0.3 修订说明','旧版 v0.2.0 的数据、录音和结果保留；新版不覆盖旧发布资产。','## 修改了什么',
           '- 时间字段解析为同一时刻后比较；规定为集合的字段忽略排列顺序，并保留重复数及布尔类型语义。',
           '- 聊天默认允许相关、权限内的只读查询；明确禁止查询按轮次记录。未经授权写入仍硬失败，冗余查询不再自动判失败。',
           '- 写操作逐轮核对对象、字段和值；不能提前用未来授权。错误写入后改回仍会留下失败证据。',
           '- 开放题改为用户约束和实际历史评分，不再要求照参考剧本选人物、词语或谜底。数字游戏首数改正为一、更正后为五。',
           '- 重复取消已取消安排返回成功；播放新内容先验证权限，再停止同设备旧会话；失败时不改旧会话。',
           '## 重跑范围与来源',
           '46题修订输入，共53段新增输入WAV通过听音QC。完整回放3000条旧轨迹后，另有5题的实际沙箱返回不同，合计51题×3系统=153次真实重跑。其余2847条保留原输出，并核验全部工具返回、前后状态及最终状态逐项完全一致。',
           '所有有可听输出的记录统一交给 Qwen3.8-Omni-Flash，温度0，采用 source_constraints_audio_v0.3。未完成听音时保持待评分，无音频的执行失败维度为NA。',
           'DeepSeek v4.1 Flash 的本次审题只走官方 api.deepseek.com（调用名 deepseek-flash）；新增合成与判官使用用户指定的北京百炼空间。历史作者记录不改写来源。',
           '试听页复查后，对全部400道聊天题的禁用条款进行了同类排查，7题澄清为“没有真实依据时不得声称已经查询”，并去除口语练习中的泛化禁工具表述。没有改变用户输入、工具轨迹或模型录音；三组对应21条记录在同一判官协议下重新校验。修订前证据保留，选择依据是用户要求与工具能力，不是模型得分。',
           '## 原始问题的独立复算',
           '下表仅替换一条规则并保持旧判官结果不变，用于核查外部审阅指出的影响；不是新版正式成绩。',
           '|系统|等价状态影响题数/检查数|仅修比较失败转通过|仅因禁工具失败的全只读题|','|---|---:|---:|---:|']
    for system,a in audits.items():lines.append(f"|{system}|{len(a['time_equivalence_affected_cases'])}/{a['time_equivalence_affected_checks']}|{len(a['time_only_counterfactual_fail_to_pass'])}|{len(a['read_only_no_tools_counterfactual_fail_to_pass'])}|")
    lines+=['## 新旧正式结果','新输入题与沙箱改变题并非完全相同的试验条件。其余题虽然保留输出，但评分规则、判官协议与服务路由发生改变，因此新版差值不能解释为模型能力提升。',
            '|系统|已判定|旧通过|新通过|失败转通过|通过转失败|','|---|---:|---:|---:|---:|---:|']
    for system,a in audits.items():
        b=a['current_comparison'];lines.append('|'+system+'|'+'|'.join(str(b.get(k,0)) for k in ['decided','old_passed','new_passed','fail_to_pass','pass_to_fail'])+'|')
    if not result['complete']:lines+=['当前仍在测评，以上只列已产生新判定的题，不能作为最终通过率。']
    lines+=['## 验证与边界','全部1000题经过结构、参考轨迹与规则检查；新增正反例覆盖时间格式、错误值后恢复、未来授权、重复取消与媒体替换原子性。两条独立真实语音对照验证了从一开始时“一”为对、“二”为错。它们不代表一般判官准确率，仍没有正式人评校准。',
            '7道长故事要求按预算压力另报，同时保留1000题全量分母。C16_015提出等待两分钟，但固定脚本没有测量该等待，不声称验证实时交互。',
            '另行读取全部7道压力题、三系统共21条记录的真实WAV时长。发现Qwen 4B的C13_020虽被判通过，全题音频也只有185.84秒，低于要求的七八分钟。原始评分保留，明确标注判官漏检，详见[时长核验](STORY_DURATION_AUDIT.md)；不把这一通过宣称为长故事要求已满足。',
            '单种子、单判官、合成普通话、不同部署精度等限制继续保留。逐轮写授权支持规定的意图、拆分更新及恢复重试，不宣称穷举任意合法等价操作策略。',
            '## 可核验文件',
            '- data/revision/dialogue_edits.json 与 reports/revision/dialogue_changes.json：每处输入的前后文本。',
            '- data/revision/read_claim_clarifications.json 与 reports/revision/read_claim_clarification.json：7题查询声明约束的局部澄清及前后哈希。',
            '- data/revision/audit_original、audit_context_v2、audit_final 与 constraint_overrides.json：机器原始审题和后续取舍；未提供被测模型得分。',
            '- reports/revision/replay_plan.json：3000条回放与51题对称重跑清单。',
            '- reports/revision/score_changes.json：每题新旧结果与变更原因；v0.2_final_scores.json 保留原始摘要。',
            '- spec/judge_protocols/source_constraints_audio_v0.3.json：新判官协议和缓存定义。',
            '- runs/<system>/<case>.json 的 revision：原录音复用依据或本次真实执行来源。']
    (ROOT/'docs/REVISION_v0.3.md').write_text(re.sub(r'\|\n\n(?=\|)','|\n','\n\n'.join(lines))+'\n','utf-8')
    print(json.dumps({'complete':result['complete'],'original_rule_audit':{s:{'time_cases':len(a['time_equivalence_affected_cases']),'time_checks':a['time_equivalence_affected_checks'],'time_flips':len(a['time_only_counterfactual_fail_to_pass']),'read_only_flips':len(a['read_only_no_tools_counterfactual_fail_to_pass'])} for s,a in audits.items()}}),flush=True)

if __name__=='__main__':main()
