import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const code=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const root=process.env.HOMEVOICE_DATA_ROOT??path.join(code,'benchmark');
const read=async p=>JSON.parse(await fs.readFile(path.join(root,p),'utf8'));
const [summary,cases,runs,scenes,tools]=await Promise.all(['reports/summary.json','reports/case_overview.json','reports/run_overview.json','reports/scene_overview.json','spec/sandbox.json'].map(read));
const [calibration,sourceLint]=await Promise.all(['reports/scoring_review_overview.json','reports/spoken_source_lint.json'].map(read));
const out=path.join(root,'outputs/homevoicebench-v040');const preview=path.join(root,'cache/workbook-preview');await fs.mkdir(out,{recursive:true});await fs.mkdir(preview,{recursive:true});
const wb=Workbook.create();const sheets=Object.fromEntries(['Overview','Calibration','DataIssues','Cases','Runs','Scenarios','Groups','Tools'].map(n=>[n,wb.worksheets.add(n)]));
const col=n=>{let s='';while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26);}return s;};
function table(sh,title,headers,rows,widths,source){
 const end=rows.length+4,last=col(headers.length);sh.showGridLines=false;
 sh.getRange(`A1:${last}${end}`).format={font:{name:'Arial',size:11,color:'#25384A'},rowHeight:25,verticalAlignment:'center'};
 sh.getRange('A2').values=[[title]];sh.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:'#25384A'};
 sh.getRange('A3').values=[[source]];sh.getRange('A3').format.font={name:'Arial',size:10,color:'#647587'};
 sh.getRange(`A4:${last}4`).values=[headers];sh.getRange(`A4:${last}4`).format={fill:'#314C67',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:32,horizontalAlignment:'center'};
 if(rows.length)sh.getRange(`A5:${last}${end}`).values=rows;
 widths.forEach((w,i)=>sh.getRange(`${col(i+1)}1:${col(i+1)}${end}`).format.columnWidth=w);
 if(rows.length)sh.tables.add(`A4:${last}${end}`,true,sh.name+'Data');sh.freezePanes.freezeRows(4);sh.freezePanes.freezeColumns(1);return end;
}
const ce=table(sheets.Cases,`${cases.length} 道语音测试题`,['题号','类别','场景','难度','轮数','题组','标题','第1轮','第2轮','第3轮','第4轮','第5轮','音频就绪','参考调用数','数据来源'],cases.map(c=>[c.case_id,c.category,c.scene_id,c.difficulty,c.turn_count,c.group_id,c.title,...Array.from({length:5},(_,i)=>c.user_texts[i]??null),c.audio_ready?1:0,c.reference_tool_calls,c.source_path]),[14,10,10,12,8,24,35,62,62,62,62,62,13,13,42],'来源：data/cases；原稿用于制题和TTS，被测模型接收用户声音。');
sheets.Cases.getRange(`G5:L${ce}`).format.wrapText=true;sheets.Cases.getRange(`A5:O${ce}`).format.rowHeight=60;
const systems=['edge_native','qwen35_2b','qwen35_4b'],lookup=new Map(runs.map(r=>[r.system_id+'/'+r.case_id,r]));
const runrows=systems.flatMap(s=>cases.map(c=>{const r=lookup.get(s+'/'+c.case_id);return [s,c.case_id,c.category,c.difficulty,c.turn_count,r?.execution_status??'pending',r?.case_pass==null?0:1,r?.case_pass==null?null:Number(r.case_pass),r?.judged?1:0,r?.mean_score??null,r?.tool_calls??null,r?.wall_seconds_interaction??null,(r?.flags??[]).join('; '),r?.failure_detail?.stage??null,r?.audio_fact_review_required?1:0,r?.run_path??null,r?.case_pass_primary==null?null:Number(r.case_pass_primary),r?.review_proposed_case_pass==null?null:Number(r.review_proposed_case_pass),r?.semantic_disputed?1:0];}));
const re=table(sheets.Runs,'三系统逐题实测记录',['系统','题号','类别','难度','计划轮数','执行状态','已判定','任务通过','有听音评分','六维均分/5','工具调用','交互秒数','中断或失败原因','中断阶段','数值待复核','原始证据','初判任务通过','复核候选通过','评分分歧'],runrows,[20,14,10,12,12,14,12,13,15,15,13,14,65,25,14,52,16,16,14],'来源：runs；任务采用最终裁定，质量保留听音初评。交互秒数不含全部离线ASR/TTS。');
sheets.Runs.getRange(`J5:J${re}`).setNumberFormat('0.00');sheets.Runs.getRange(`L5:L${re}`).setNumberFormat('0.00');
sheets.Runs.getRange(`H5:H${re}`).conditionalFormats.add('cellIs',{operator:'equal',formula:0,format:{fill:'#FBE9E5',font:{color:'#963F32'}}});
table(sheets.Scenarios,'30 个工具场景与 20 个聊天场景',['场景','类别','名称','题数','语音就绪','用户轮数','主要考察'],scenes.map(s=>[s.scene_id,s.category,s.title,s.case_count,s.ready_cases,s.normal_user_turns,s.focus??s.family??s.subcategory??'']),[12,12,36,12,14,14,85],'来源：homevoice/catalog.py 与逐题索引。');
const groups=summary.group_progression??[];
table(sheets.Groups,'同一任务逐步加难的完整题组',['系统','题组','第1级','第2级','第3级','第4级','首次观察到失败级别'],groups.map(g=>[g.system_id,g.family,...Array.from({length:4},(_,i)=>{const r=g.results.find(r=>r.level===i+1);return r?.passed==null?'尚未判定':r.passed?'通过':'未通过';}),g.first_failed_level??null]),[21,25,14,14,14,14,25],'来源：逐题实测；首次失败是本次观察，不能视为确定的通用能力阈值。');
const te=table(sheets.Tools,'10 个常用工具和 2 个异步扩展工具',['工具','层级','用途','必需参数','输入字段','完整合同'],tools.tools.map(t=>[t.name,tools.core_tool_names.includes(t.name)?'常用':'异步扩展',t.description,(t.input_schema.required??[]).join(', '),Object.keys(t.input_schema.properties??{}).join(', '),'spec/sandbox.json']),[23,14,80,35,60,25],'来源：冻结工具合同；两类题的全部系统使用相同工具配置。');
sheets.Tools.getRange(`C5:E${te}`).format.wrapText=true;sheets.Tools.getRange(`A5:F${te}`).format.rowHeight=70;
const he=table(sheets.Calibration,`${calibration.records} 份机器复裁记录 · ${calibration.unique_cases} 道题`,['系统','题号','分歧检查项','初判','复核候选','最终任务结论','重新听原音频','第一轮用户输入','试听链接','证据SHA256'],calibration.rows.map(r=>[r.system_id,r.case_id,r.check_disagreements.map(x=>x.check_id).join(', '),r.case_pass_primary?'通过':'不通过',r.review_proposed_case_pass?'通过':'不通过',r.case_pass_final==null?'待裁定':r.case_pass_final?'通过':'不通过',r.audio_adjudicated?'是':'否',r.user_texts[0],r.review_url,r.evidence_sha256]),[21,14,24,12,12,16,16,70,85,70],'依预先固定口径处理分歧：同一判官重新听原音频；不是独立人工校准。初判和复核均保留。');
if(he>=5){sheets.Calibration.getRange(`H5:J${he}`).format.wrapText=true;sheets.Calibration.getRange(`A5:J${he}`).format.rowHeight=65;}
const le=table(sheets.DataIssues,`${sourceLint.affected_cases} 道题的原稿待修项`,['题号','轮次','混入的字段','当前原稿','处理状态'],sourceLint.rows.map(r=>[r.case_id,r.node_id,r.residual_terms.join(', '),r.text,'待处理']),[14,10,38,95,40],'来源：当前全量原稿检查；零行表示字段泄漏检查通过。修正历史保留在协议文档和开发存档。');
if(le>=5){sheets.DataIssues.getRange(`C5:E${le}`).format.wrapText=true;sheets.DataIssues.getRange(`A5:E${le}`).format.rowHeight=65;}
const ov=sheets.Overview;ov.showGridLines=false;ov.tabColor='#314C67';ov.getRange('A1:I35').format={font:{name:'Arial',size:11,color:'#25384A'},rowHeight:27,verticalAlignment:'center'};
[22,12,13,13,13,14,14,16,16].forEach((w,i)=>ov.getRange(`${col(i+1)}1:${col(i+1)}35`).format.columnWidth=w);
ov.getRange('A2').values=[[`HomeVoiceBench-ZH v0.4 ${summary.split==='development'?'开发验证':'正式测评'}`]];ov.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:'#25384A'};
ov.getRange('A4').values=[['总题数']];ov.getRange('B4').formulas=[[`=COUNTA('Cases'!A5:A${ce})`]];ov.getRange('D4').values=[['工具 / 聊天']];ov.getRange('F4:G4').values=[[summary.dataset.tool_cases,summary.dataset.chat_cases]];
ov.getRange('A6').values=[['三组内容和工具决策均为 greedy；判官温度 0。']];ov.getRange('A7').values=[['任务采用最终裁定；质量保留听音初评，无声音不记零分。']];
ov.getRange('A9:I9').values=[['系统','类别','计划题数','已执行','已判定','任务通过','听音题数','任务通过率','质量均分/5']];ov.getRange('A9:I9').format={fill:'#314C67',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:32,horizontalAlignment:'center'};
const pairs=systems.flatMap(s=>['all','tool','chat'].map(c=>[s,c]));ov.getRange('A10:B18').values=pairs;
const rs=`'Runs'!$A$5:$A$${re}`,rc=`'Runs'!$C$5:$C$${re}`,ex=`'Runs'!$F$5:$F$${re}`,dec=`'Runs'!$G$5:$G$${re}`,pass=`'Runs'!$H$5:$H$${re}`,aud=`'Runs'!$I$5:$I$${re}`,score=`'Runs'!$J$5:$J$${re}`;
ov.getRange('C10:I18').formulas=pairs.map(([s,c],i)=>{const r=i+10,cond=`${rs},$A${r}`+(c==='all'?'':`,${rc},$B${r}`);return [c==='all'?'=$B$4':`=COUNTIFS('Cases'!$B$5:$B$${ce},$B${r})`,`=COUNTIFS(${cond},${ex},"<>pending")`,`=SUMIFS(${dec},${cond})`,`=SUMIFS(${pass},${cond})`,`=SUMIFS(${aud},${cond})`,`=IF(E${r}=C${r},F${r}/C${r},"待裁定")`,`=IF(G${r}>0,SUMIFS(${score},${cond})/G${r},"NA")`];});
ov.getRange('H10:H18').setNumberFormat('0.0%');ov.getRange('I10:I18').setNumberFormat('0.00');
ov.getRange('A21').values=[['设计：40% 成组题；60% 基础、30% 标准、10% 挑战。']];ov.getRange('A22').values=[['成组题保留共同前缀，增加更正、指代和约束；每题独立重置环境。']];ov.getRange('A23').values=[['语音为合成普通话；单 seed、单判官，尚无正式人评校准。']];ov.getRange('A25').values=[['分歧按固定协议重新听音裁定；不选择较高分。']];
ov.getRange('A26').values=[[`Calibration列出${calibration.records}份争议；DataIssues列出${sourceLint.affected_cases}道原稿待修题。`]];
ov.getRange('A28:F28').values=[['系统','初判通过','复核候选通过','最终通过','曾有分歧','机器复裁']];ov.getRange('A28:F28').format={fill:'#314C67',font:{bold:true,color:'#FFFFFF'}};
ov.getRange('A29:A31').values=systems.map(s=>[s]);
ov.getRange('B29:E31').formulas=systems.map((s,i)=>{const r=i+29,cond=`${rs},$A${r}`;return [`=SUMIFS('Runs'!$Q$5:$Q$${re},${cond})`,`=SUMIFS('Runs'!$R$5:$R$${re},${cond})`,`=SUMIFS(${pass},${cond})`,`=SUMIFS('Runs'!$S$5:$S$${re},${cond})`];});
ov.getRange('F29:F31').values=systems.map(s=>[summary.semantic_consistency_review.systems.find(r=>r.system_id===s).audio_adjudicated]);
ov.getRange('A33').values=[['语义复核看听写；机器复裁重新听音，均不是独立人工金标。']];
ov.getRange('A24').values=[['新版难度、工具与解码均有变化，不能把新旧通过率差异归因于模型进步。']];
ov.getRange('C10:I18').format.horizontalAlignment='center';
sheets.Cases.getRange(`E5:E${ce}`).format.horizontalAlignment='center';
sheets.Runs.getRange(`C5:I${re}`).format.horizontalAlignment='center';
sheets.Scenarios.getRange(`D5:F${scenes.length+4}`).format.horizontalAlignment='center';
sheets.Groups.getRange(`C5:G${groups.length+4}`).format.horizontalAlignment='center';
wb.recalculate();
const checked=ov.getRange('C10:I18').values;
for(let i=0;i<pairs.length;i++){const [s,c]=pairs[i],r=summary.systems.find(x=>x.system_id===s&&x.category===c);if(checked[i][0]!==r.planned||checked[i][2]!==r.decided_count||checked[i][3]!==r.passed_count)throw Error('Summary reconciliation failed '+s+'/'+c);}
// Verify the actual dependency updates, then restore the source before export.
const savedPass=sheets.Runs.getRange('H5').values[0][0],savedTotal=ov.getRange('F10').values[0][0];
if(savedPass===0||savedPass===1){
 sheets.Runs.getRange('H5').values=[[1-savedPass]];wb.recalculate();
 if(ov.getRange('F10').values[0][0]!==savedTotal+1-2*savedPass)throw Error('Summary recalculation did not follow run input');
 sheets.Runs.getRange('H5').values=[[savedPass]];wb.recalculate();
 if(ov.getRange('F10').values[0][0]!==savedTotal)throw Error('Source restoration failed');
}
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},maxChars:3000});await fs.writeFile(path.join(preview,'formula-scan.json'),errors.ndjson);
for(const [name,range] of [['Overview','A1:I34'],['Calibration','A1:G8'],['DataIssues','A1:E8'],['Cases','A1:H8'],['Runs','A1:L9'],['Scenarios','A1:G8'],['Groups','A1:G9'],['Tools','A1:F8']]){
 const blob=await wb.render({sheetName:name,range,scale:1.3,format:'png'});await fs.writeFile(path.join(preview,name+'.png'),new Uint8Array(await blob.arrayBuffer()));
}
const output=await SpreadsheetFile.exportXlsx(wb);await output.save(path.join(out,'HomeVoiceBench-ZH-v0.4.xlsx'));console.log(JSON.stringify({file:path.join(out,'HomeVoiceBench-ZH-v0.4.xlsx'),cases:cases.length,runs:runs.length,reconciled:true}));
