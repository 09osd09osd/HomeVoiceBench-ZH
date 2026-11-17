"""Measure all preselected story-budget cases without changing judge scores.

Approximate requests are reported against their nominal duration, not converted
into a new hard threshold. A duration change ends the earlier request window.
The whole-case duration includes even non-story replies: it is a generous upper
bound, not a claim that all of that audio is story narration.
"""
import datetime
import hashlib
import json
from pathlib import Path
import wave

ROOT = Path(__file__).resolve().parents[1]
SYSTEMS = ['edge_native', 'qwen35_2b', 'qwen35_4b']
REQUESTS = {
    'C02_013': ('U1', '二十分钟左右', 1200, None, 'approximate', 'U3'),
    'C13_001': ('U1', '三四分钟', 180, 240, 'range', None),
    'C13_002': ('U1', '三分钟左右', 180, None, 'approximate', None),
    'C13_003': ('U1', '三四分钟', 180, 240, 'range', None),
    'C13_004': ('U1', '三分钟左右', 180, None, 'approximate', None),
    'C13_017': ('U2', '六分钟左右', 360, None, 'approximate', None),
    'C13_020': ('U2', '七八分钟', 420, 480, 'range', 'U5'),
}


def read(relative):
    return json.loads((ROOT / relative).read_text('utf-8'))


def main():
    overview = read('reports/case_overview.json')
    selected = {c['case_id'] for c in overview if c['reporting_partition'] == 'budget_stress'}
    if selected != set(REQUESTS):
        raise ValueError('Duration audit must cover every preselected budget-stress case')
    rows = []
    for case_id, (node_id, phrase, target, upper, kind, stop) in REQUESTS.items():
        case = read(f'data/cases/{case_id}.json')
        nodes = case['interaction']['nodes']
        node = next(n for n in nodes if n['id'] == node_id)
        if phrase not in node['user_text']:
            raise ValueError('Source duration request changed: ' + case_id)
        ids = [n['id'] for n in nodes]
        window = set(ids[ids.index(node_id):ids.index(stop) if stop else len(ids)])
        for system in SYSTEMS:
            path = ROOT / f'runs/{system}/{case_id}.json'
            run = json.loads(path.read_text('utf-8'))
            seconds = []
            for turn in run['turns']:
                audio = turn.get('assistant_audio')
                duration = 0.0
                if audio:
                    with wave.open(str(ROOT / audio['path']), 'rb') as wav:
                        duration = wav.getnframes() / wav.getframerate()
                    if abs(duration - audio['duration_s']) > 0.02:
                        raise ValueError('Stored duration mismatch: ' + audio['path'])
                seconds.append({'node_id': turn['node_id'], 'seconds': round(duration, 3)})
            total = round(sum(t['seconds'] for t in seconds), 3)
            window_seconds = round(sum(t['seconds'] for t in seconds if t['node_id'] in window), 3)
            rows.append({
                'system_id': system, 'case_id': case_id, 'request_node_id': node_id,
                'source_user_text': node['user_text'], 'duration_phrase': phrase,
                'target_kind': kind, 'nominal_or_lower_seconds': target,
                'upper_seconds': upper, 'request_window_nodes': sorted(window),
                'window_end_note': ('U3 changes the request to at most ten minutes; no lower bound after U3'
                                    if case_id == 'C02_013' else 'U5 explicitly asks for a brief ending'
                                    if case_id == 'C13_020' else 'end of case'),
                'request_window_audio_seconds': window_seconds,
                'whole_case_audio_seconds': total,
                'whole_case_to_target_ratio': round(total / target, 4),
                'whole_case_below_nominal_or_lower': total < target,
                'formal_case_pass': run['case_pass'],
                'judge_pass_with_duration_discrepancy': run['case_pass'] is True and total < target,
                'per_turn_durations': seconds,
                'run_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            })
    result = {
        'version': '0.3.0', 'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'all 7 preselected budget-stress cases, all 3 systems',
        'measurement': 'WAV frame count divided by sample rate; all assistant audio, including non-story replies',
        'scoring_policy': 'Diagnostic only. Original audio-judge scores and formal pass rates are preserved; approximate durations are not retroactively assigned a hard tolerance.',
        'interpretation': 'Even whole-case audio shorter than the nominal/range lower duration signals a budget mismatch, but this is not a complete semantic story evaluator. C02_013 later changes to an upper-bound-only request.',
        'rows': rows,
        'judge_disagreements': [{'system_id': r['system_id'], 'case_id': r['case_id']} for r in rows if r['judge_pass_with_duration_discrepancy']],
    }
    target = ROOT / 'reports/revision/story_duration_audit.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    lines = ['# 长故事时长核验', '',
             '覆盖预先划入预算压力分组的全部7题、三组共21条记录。直接读取WAV帧数计算时长；没有重新调用模型，也没有手改判官分数。', '',
             '下表的“全题音频”把解释、道歉和收尾也计入，已是故事时长的宽松上限；它不代表真正讲述故事的时长。“左右”只与标称值比较，不新增任意通过阈值。C02_013在U3改成十分钟以内，后续只有上限，不能继续套用二十分钟下限。', '',
             '|题目|系统|用户原始时长要求|对应阶段音频/秒|全题音频/秒|判官及规则的原始结论|',
             '|---|---|---|---:|---:|---|']
    for r in rows:
        lines.append(f"|{r['case_id']}|{r['system_id']}|{r['duration_phrase']}|{r['request_window_audio_seconds']:.2f}|{r['whole_case_audio_seconds']:.2f}|{'通过；存在时长分歧' if r['judge_pass_with_duration_discrepancy'] else '通过' if r['formal_case_pass'] else '未通过'}|")
    lines += ['', '已确认分歧：Qwen 4B 的 C13_020 要求七八分钟；即使合计全题所有回复也未达到七分钟，但原始判官给了通过。该判断保留作为判官错误样例，不能把预算压力表中的一次通过解释为已完成所要求的长故事。', '',
              '常规993题单独汇报；全量1000题及原始判官口径保留。正式人评校准尚未开展。逐轮音频时长、请求窗口和运行文件哈希见 [story_duration_audit.json](../reports/revision/story_duration_audit.json)。', '']
    (ROOT / 'docs/STORY_DURATION_AUDIT.md').write_text('\n'.join(lines), 'utf-8')
    print(json.dumps({'rows': len(rows), 'judge_disagreements': result['judge_disagreements']}))


if __name__ == '__main__':
    main()
