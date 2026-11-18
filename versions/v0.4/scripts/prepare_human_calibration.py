"""Package evidence, not agent-authored human labels, for the chosen manual review."""
import datetime,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import CODE_ROOT,ROOT
from homevoice.human_review import SYSTEMS,read

rows=[]
for sid in SYSTEMS:
    for p in sorted((ROOT/'runs'/sid).glob('*.json')):
        r=read(p)
        if (r.get('semantic_review') or {}).get('decision_status')!='disputed':continue
        c=read(ROOT/'data/cases'/p.name);a=r['audio_judge']['result'];b=r['semantic_review']['result']
        first={x['check_id']:x for x in a['semantic_checks']};second={x['check_id']:x for x in b['checks']}
        differences=[{'check_id':key,'primary':first.get(key),'review':second.get(key)} for key in sorted(first.keys()|second.keys()) if (first.get(key) or {}).get('passed')!=(second.get(key) or {}).get('passed')]
        rows.append({'case_id':p.stem,'system_id':sid,'category':c['classification']['category'],'title':c['identity']['title'],'user_texts':[n['user_text'] for n in c['interaction']['nodes']],'case_pass_primary':r['case_pass_primary'],'review_proposed_case_pass':r['semantic_review']['proposed_case_pass'],'check_disagreements':differences,'primary_critical_failures':a['critical_failures'],'review_critical_failures':b['critical_failures'],'evidence_sha256':r['audio_judge']['evidence_sha256'],'human_verdict':None,'human_reason':None,'review_url':f'http://127.0.0.1:18788/review/?dataset=pilot&queue=calibration#case={p.stem}&tab=compare'})
report={'status':'awaiting_human_calibration','prepared_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'records':len(rows),'unique_cases':len({r['case_id'] for r in rows}),'manifest_sha256':hashlib.sha256((ROOT/'data/manifest.json').read_bytes()).hexdigest(),'labels_are_blank':True,'automatic_score_changes':False,'rows':rows}
(ROOT/'reports/human_calibration_queue.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
labels={'edge_native':'实验组 EdgeInstant','qwen35_2b':'Qwen 2B 级联','qwen35_4b':'Qwen 4B 级联'}
lines=['# 100题开发集：人工校准说明','','当前待校准 **25份模型结果，涉及24道题**。这不是25道新题；同一道题可能有两组模型都需要裁定。人工结论全部留空，正式1000题尚未启动。','','[直接打开争议试听队列](http://127.0.0.1:18788/review/?dataset=pilot&queue=calibration)。若服务未运行，双击上一层的 `启动v0.4试听.cmd`。','','## 怎样完成一份判断','','1. 在“逐轮试听”听用户输入和被标记模型的全部实际回答；多轮题要看前后文。没有朗读的文字不能替代实际音频。','2. 查看“标准与预期”里的用户必须要求；工具题再看真实返回、状态和逐轮授权。参考答案只是一条示例路径，不是唯一说法。','3. 先形成自己的判断，再到“判官评分”比较初判、复核理由。两次来自同一个模型，不能当作两个人已经独立投票。','4. 到“人工记录”，只需优先填写黄色框“本次需要人工校准”的模型：选“人工通过 / 人工不通过 / 暂不确定”，再写一句理由，指出轮次和依据。','5. 用“下一题”继续。左侧“已裁定 x/25”只统计有理由、证据匹配的通过/不通过；“已听完”与“同意原判定”均不替代人工结论。','6. 点击右上角“导出评审 JSON”。把导出文件位置告诉维护者；可随时导出、下次导入接着做。CSV仅供查看。','','## 这次采用的判断口径','','- **通过**：完成实际用户任务，满足必需约束；没有未经授权的写入、虚构执行结果或其他严重错误。正常执行和程序硬规则仍需满足。','- **不通过**：指出具体遗漏、错误或违规，不因答案不够漂亮、没有照抄参考、缺少用户没要求的内容就判失败。语言自然程度等质量另记，不用最低维度分卡通过。','- **暂不确定**：听不清、语义边界含混，或题目/评分规则本身有问题；请写出疑点，先不强行二选一。','- 例如，“如果这是一台智能设备，我可以查询”要区分假设与已执行声明；“我刚查到它的状态”需要真实工具证据。实际是否恰当仍应结合整段对话。','- 工具的等价时间、当前轮的对象/字段/允许值，以及只读查询与写操作的区别，由程序检查共同约束。人工认为通过却与硬检查冲突时，先复核规则，不能直接覆盖。','','## 已知数据问题，单独处理','','T06_101—104、T11_101—104、T12_101 的用户语音原稿混入 brightness_pct、mode/auto、volume_pct 等实现字段，共9题、21个输入轮次。它们与25份语义争议无重叠。新生成流程已经加入拦截；当前录音和成绩保留。后续用自然中文修正，并对三组模型对称重跑受影响的9题；不能只修对某一个模型不利的题。','','## 收到人工结论后如何继续','','先校验数据集版本、证据哈希和理由，整理“判官误判 / 规则不清 / 数据问题 / 模型确实失败”。若修改评分规则，对所有符合条件的开发记录统一复评；若修改用户输入，对三组对称重跑受影响题。保留旧结果和变更记录，再复核未通过的开发反例与数据检查。','','这25份是刻意选出的争议样本，不能用其一致率代表判官在全部题目上的准确率，也不能为了达到某一目标通过率而选择标签。校准完成后仍建议抽查两次一致的结果；只有验收条件真正满足，才进入正式1000题。','','导入工具只生成校准分析文件，不修改 `runs` 或正式通过率：','','```powershell','python -X utf8 scripts/collect_human_review.py --input "C:\\路径\\人工评审.json"','```','','## 争议清单','','| 系统 | 题号 | 分歧检查项 | 试听 |','|---|---|---|---|']
for r in rows:lines.append(f'| {labels[r["system_id"]]} | {r["case_id"]} | {", ".join(x["check_id"] for x in r["check_disagreements"]) or "严重错误/整体结论"} | [打开]({r["review_url"]}) |')
lines+=['','导出JSON字段：`format/dataset_key/manifest_sha256`标识协议和输入版本；`records[].case_id`是题号；`systems.<模型>.verdict`为pending/pass/fail/uncertain；`note`为依据；`evidence_sha256`绑定当前录音、工具轨迹和题目；`updated_at`为记录时间。`opinion`只记录对初判的意见；`done/flag`只管理试听进度，不是分数。','']
(CODE_ROOT/'docs/HUMAN_CALIBRATION.md').write_text('\n'.join(lines),'utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='rows'},ensure_ascii=False))
