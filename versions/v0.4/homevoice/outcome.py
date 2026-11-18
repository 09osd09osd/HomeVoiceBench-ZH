"""Task gate is explicit; six quality dimensions are reported separately."""
def task_pass(run,case,judgment):
    required={c['id'] for c in case['evaluation']['checks'] if c['required']}
    rules={c['check_id']:c['passed'] for c in run['rule_checks']}
    semantic={c['check_id']:c['passed'] for c in judgment['semantic_checks']}
    checks={**rules,**semantic}
    return (run['execution']['status']=='completed' and all(checks.get(k) is True for k in required)
            and not judgment['critical_failures']
            and not any((t.get('assistant_audio') or {}).get('hit_frame_budget',False) for t in run['turns']))
