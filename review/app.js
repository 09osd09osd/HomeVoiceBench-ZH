/* Local-only review UI. No model calls, analytics or remote storage. */
(function () {
  'use strict';
  const C=window.ReviewCore, E=C.escapeHTML, $=id=>document.getElementById(id);
  const {SYSTEMS,LABELS}=C;
  const state={source:null,index:null,runMap:new Map(),cases:new Map(),filtered:[],selected:null,bundle:null,tab:'compare',page:0,pageSize:35,revision:0,speed:1,notes:Object.create(null),key:'',cache:new Map(),queue:[],toastTimer:null,filters:{search:'',category:'all',scene:'all',turns:'all',review:'all',result:'all',sort:'id'}};
  const jsonText=value=>JSON.stringify(value,null,2)??'无';
  const pretty=value=>value===undefined?'无':value===null?'空':typeof value==='object'?JSON.stringify(value):String(value);
  const percentScore=value=>Number.isFinite(value)?value.toFixed(2):'NA';
  const badge=(value,yes='严格通过',no='未通过')=>`<span class="badge ${value===true?'pass':value===false?'fail':'pending'}">${value===true?yes:value===false?no:'暂无结论'}</span>`;
  const detail=(title,content,open=false)=>`<details class="details" ${open?'open':''}><summary>${E(title)}</summary><div class="details-body">${content}</div></details>`;
  const raw=(title,value)=>detail(title,`<pre class="raw-json">${E(jsonText(value))}</pre>`);
  function toast(message) {clearTimeout(state.toastTimer);$('toast').textContent=message;$('toast').classList.remove('hidden');state.toastTimer=setTimeout(()=>$('toast').classList.add('hidden'),4500);}

  class HttpSource {
    async json(path) {if(!C.safePath(path))throw Error('不允许读取这个路径');const r=await fetch('/files/'+path,{cache:'no-cache'});if(!r.ok)throw Error('文件读取失败：'+path+'（'+r.status+'）');return r.json();}
    async index() {const r=await fetch('/api/index',{cache:'no-cache'});if(!r.ok)throw Error('本地服务尚未准备好');return r.json();}
    async audio(path) {if(!C.safePath(path))throw Error('无效音频路径');return '/files/'+path;}
    async file(path) {if(!C.safePath(path))throw Error('无效文件路径');const r=await fetch('/files/'+path);if(!r.ok)throw Error('文件不存在：'+path);return r.blob();}
    clearURLs() {}
  }
  class FolderSource {
    constructor(handle,files=null) {this.handle=handle;this.files=files;this.urls=new Map();}
    async file(path) {
      if(!C.safePath(path))throw Error('不允许读取这个路径');
      if(this.files){const file=this.files.get(path);if(!file)throw Error('未找到 '+path);return file;}
      const parts=path.split('/');let directory=this.handle;
      for(const part of parts.slice(0,-1))directory=await directory.getDirectoryHandle(part);
      return (await directory.getFileHandle(parts.at(-1))).getFile();
    }
    async json(path){return JSON.parse(await (await this.file(path)).text());}
    async index(){
      const names=['summary','case_overview','scene_overview','run_overview'];
      const values=await Promise.all(names.map(name=>this.json('reports/'+name+'.json')));
      const manifest=await (await this.file('data/manifest.json')).arrayBuffer();
      const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',manifest)),b=>b.toString(16).padStart(2,'0')).join('');
      return {...Object.fromEntries(names.map((name,i)=>[name,values[i]])),root_name:this.handle?.name??'HomeVoiceBench-ZH',manifest_sha256:digest};
    }
    async audio(path){if(!this.urls.has(path))this.urls.set(path,URL.createObjectURL(await this.file(path)));return this.urls.get(path);}
    clearURLs(){for(const value of this.urls.values())URL.revokeObjectURL(value);this.urls.clear();}
  }
  function stopAudio(){state.queue=[];document.querySelectorAll('audio').forEach(audio=>audio.pause());}
  function resetMedia(){stopAudio();state.source?.clearURLs();}
  function connectError(error){$('connection-error').textContent='读取失败：'+error.message+'。请选择包含 data、runs、reports、assets 的 HomeVoiceBench-ZH 根目录。';$('connection-error').classList.remove('hidden');}
  async function connect(source){
    resetMedia();state.revision++;$('source-label').textContent='正在读取本地目录…';$('connection-error').classList.add('hidden');
    try{
      const index=await source.index();
      if(!Array.isArray(index.case_overview)||!Array.isArray(index.run_overview)||!Array.isArray(index.scene_overview)||!index.manifest_sha256)throw Error('数据目录缺少完整索引');
      if(new Set(index.case_overview.map(x=>x.case_id)).size!==index.case_overview.length)throw Error('题目索引含重复 ID');
      state.source=source;state.index=index;state.cache.clear();state.cases=new Map(index.case_overview.map(x=>[x.case_id,x]));state.runMap=new Map(index.run_overview.map(r=>[r.system_id+'/'+r.case_id,r]));
      state.key='homevoice-review-v2:'+index.manifest_sha256+':'+(index.summary.judge_prompt_sha256??'unknown');state.notes=Object.create(null);
      try{const saved=localStorage.getItem(state.key);if(saved){const values=C.parseReviewImport(JSON.parse(saved),state.key,new Set(state.cases.keys()));for(const row of values)state.notes[row.case_id]=row;}}catch(error){toast('已有评审记录未能载入：'+error.message);}
      $('source-label').textContent=index.root_name+' · '+index.run_overview.length.toLocaleString()+' 份结果摘要';
      $('total-count').textContent=index.case_overview.length.toLocaleString();$('welcome').classList.add('hidden');$('workspace').classList.remove('hidden');
      $('scene-filter').innerHTML='<option value="all">全部 '+index.scene_overview.length+' 个场景</option>'+index.scene_overview.map(s=>`<option value="${E(s.scene_id)}">${E(s.scene_id+' · '+s.title)}</option>`).join('');
      $('export-json').disabled=false;$('export-csv').disabled=false;
      applyFilters();const hash=new URLSearchParams(location.hash.slice(1));const desired=hash.get('case');
      if(['compare','judge','tools','expected','notes'].includes(hash.get('tab')))state.tab=hash.get('tab');
      selectCase(state.cases.has(desired)?desired:state.cases.has('T06_003')?'T06_003':index.case_overview[0]?.case_id);
    }catch(error){connectError(error);$('source-label').textContent='尚未连接数据';$('welcome').classList.remove('hidden');$('workspace').classList.add('hidden');}
  }
  async function pickFolder(){
    if(window.showDirectoryPicker){
      try{const handle=await window.showDirectoryPicker({id:'homevoice-review',mode:'read'});await connect(new FolderSource(handle));}catch(error){if(error.name!=='AbortError'){$('folder-fallback').click();toast('请选择数据集根目录。');}}
    }else $('folder-fallback').click();
  }
  $('folder-fallback').addEventListener('change',event=>{
    const files=new Map();for(const file of event.target.files){const parts=file.webkitRelativePath.split('/');const path=parts.slice(1).join('/');if(C.safePath(path))files.set(path,file);}
    if(files.size)connect(new FolderSource(null,files));event.target.value='';
  });
  function applyFilters(){
    if(!state.index)return;state.filtered=C.filterCases(state.index.case_overview,state.runMap,state.notes,state.filters);state.page=Math.min(state.page,Math.max(0,Math.ceil(state.filtered.length/state.pageSize)-1));renderList();if(state.bundle)renderHeading();
  }
  function renderList(){
    const rows=state.filtered.slice(state.page*state.pageSize,(state.page+1)*state.pageSize);
    $('review-progress').textContent='已听 '+Object.values(state.notes).filter(x=>x.done).length;
    $('match-count').textContent=state.filtered.length+' 题匹配';
    $('case-list').innerHTML=rows.length?rows.map(c=>{
      const note=state.notes[c.case_id];const short=['实','2B','4B'];
      return `<button class="case-item ${c.case_id===state.selected?'selected':''}" data-case="${E(c.case_id)}" aria-label="${E(c.case_id+' '+c.title)}" aria-pressed="${c.case_id===state.selected}"><span class="case-line"><span>${E(c.case_id)}</span><span>${note?.flag?'⚑ 需复核':note?.done?'✓ 已听':''}</span></span><strong>${E(c.title)}</strong><span class="case-bottom"><span>${c.category==='tool'?'工具':'聊天'} · ${c.turn_count} 轮</span><span class="mini-results">${SYSTEMS.map((id,i)=>{const value=state.runMap.get(id+'/'+c.case_id)?.case_pass;return `<span class="mini-status ${value===true?'pass':value===false?'fail':''}" title="${E(LABELS[id])}：${value===true?'通过':value===false?'未通过':'缺失'}">${short[i]}</span>`;}).join('')}</span></span></button>`;
    }).join(''):'<p class="empty-list">没有匹配题目。可清除关键词或调整筛选条件。</p>';
    const pages=Math.max(1,Math.ceil(state.filtered.length/state.pageSize));$('list-page').textContent=(state.page+1)+' / '+pages+' 页';$('list-prev').disabled=state.page===0;$('list-next').disabled=state.page>=pages-1;
  }
  function updateHash(){try{history.replaceState(null,'','#case='+state.selected+'&tab='+state.tab);}catch(_error){}}
  async function selectCase(id){
    if(!id||!state.cases.has(id))return;resetMedia();const revision=++state.revision;state.selected=id;state.bundle=null;const listAt=state.filtered.findIndex(x=>x.case_id===id);if(listAt>=0)state.page=Math.floor(listAt/state.pageSize);$('main').setAttribute('aria-busy','true');renderList();$('case-list').querySelector('.selected')?.scrollIntoView({block:'nearest'});
    $('case-heading').innerHTML=`<div class="case-breadcrumb">${E(id)}</div><h1>${E(state.cases.get(id).title)}</h1>`;$('model-summary').innerHTML='';$('content').innerHTML='<div class="loading"><div class="spinner"></div>正在读取该题的三组运行记录…</div>';updateHash();
    try{
      let bundle=state.cache.get(id);
      if(!bundle){const result=await Promise.allSettled([state.source.json('data/cases/'+id+'.json'),...SYSTEMS.map(system=>state.source.json('runs/'+system+'/'+id+'.json'))]);if(result[0].status!=='fulfilled')throw result[0].reason;
        bundle={testCase:result[0].value,runs:{},errors:{}};SYSTEMS.forEach((system,i)=>{const item=result[i+1];if(item.status==='fulfilled'){if(item.value.case_id!==id||item.value.system_id!==system)throw Error('运行记录标识与文件路径不一致');bundle.runs[system]=item.value;}else bundle.errors[system]=item.reason.message;});
        state.cache.set(id,bundle);if(state.cache.size>3)state.cache.delete(state.cache.keys().next().value);
      }
      if(revision!==state.revision)return;state.bundle=bundle;$('main').setAttribute('aria-busy','false');renderHeading();renderSummary();renderContent();
    }catch(error){if(revision===state.revision)$('content').innerHTML=`<div class="inline-notice">${E(error.message)}</div>`;}
    finally{if(revision===state.revision)$('main').setAttribute('aria-busy','false');}
  }
  function renderHeading(){
    const c=state.bundle.testCase,note=state.notes[state.selected];const at=state.filtered.findIndex(x=>x.case_id===state.selected);
    $('case-heading').innerHTML=`<div class="case-topline"><div class="case-breadcrumb">${c.classification.category==='tool'?'工具调用':'家庭聊天'} / ${E(c.classification.scene_id+' '+c.classification.scene_title)}</div><div class="case-navigation"><span class="case-position">${at>=0?`${at+1} / ${state.filtered.length}`:'所选题不在当前筛选中'}</span><button class="button" data-nav="-1" ${at<=0?'disabled':''}>← 上一题</button><button class="button" data-nav="1" ${at<0||at>=state.filtered.length-1?'disabled':''}>下一题 →</button></div></div><div class="case-title-row"><h1>${E(c.identity.title)}</h1><div class="review-actions"><button class="button ${note?.flag?'flagged':''}" data-note-action="flag">${note?.flag?'⚑ 已标记复核':'⚑ 标记复核'}</button><button class="button ${note?.done?'active':'primary'}" data-note-action="done">${note?.done?'✓ 已听完':'标记已听完'}</button></div></div><div class="case-tags"><span class="tag">${E(c.identity.case_id)}</span><span class="tag">v${E(c.schema_version)} · ${c.evaluation.reporting_partition==='budget_stress'?'长语音预算压力题':'普通题'}</span><span class="tag">预设 ${c.interaction.nodes.length} 轮 · 最长 ${c.interaction.budget.max_user_turns} 轮</span><span class="tag">${E(({easy:'基础',medium:'进阶',hard:'复杂'})[c.classification.difficulty]??c.classification.difficulty)}</span><span class="tag">${E(c.model_context.actor.name)} · ${E(({adult_member:'成年家庭成员',guest:'访客',child:'儿童',owner:'家庭主人'})[c.model_context.actor.role]??c.model_context.actor.role)}</span>${c.environment.faults.length?`<span class="tag">${c.environment.faults.length} 项故障夹具</span>`:''}</div>`;
  }
  function renderSummary(){
    $('model-summary').innerHTML=SYSTEMS.map(id=>{const run=state.bundle.runs[id];return `<section class="summary-card" data-system="${id}"><div class="model-heading"><span class="model-label">${LABELS[id]}</span>${badge(run?.case_pass)}</div><div class="score-line"><strong>${percentScore(C.meanScore(run))}</strong><span>/ 5 · 整题六维均分</span></div><div class="summary-meta"><span>${run?`完成 ${run.turns.length} 轮 · ${run.execution.tool_calls} 次工具`:'未找到本地运行记录'}</span><span>${run?.execution.status==='completed'?'执行结束':run?'执行失败':'缺失'}</span></div></section>`;}).join('');
  }
  function audioHTML(path,label,role='reply',duration){
    if(!path)return '<div class="mini-note">此处没有可播放的音频记录。</div>';
    if(!C.safePath(path))return '<div class="audio-error">音频路径格式不正确。</div>';
    const filename=label.replace(/[\\/:*?"<>|]/g,'-')+'.wav';
    return `<div class="audio-wrap"><audio controls preload="none" data-audio-path="${E(path)}" data-role="${role}" aria-label="${E(label)}"></audio><div class="audio-caption"><span>${Number.isFinite(duration)?duration.toFixed(2)+' 秒':'实际录音'}</span><button data-download="${E(path)}" data-filename="${E(filename)}">下载音频 ↗</button></div><div class="audio-error hidden" role="status"></div></div>`;
  }
  function hydrateAudio(){
    const revision=state.revision;
    document.querySelectorAll('audio[data-audio-path]').forEach(async audio=>{
      try{const url=await state.source.audio(audio.dataset.audioPath);if(revision!==state.revision||!audio.isConnected)return;audio.src=url;audio.playbackRate=state.speed;}
      catch(error){if(audio.isConnected){const node=audio.parentElement.querySelector('.audio-error');node.textContent='音频文件未找到，请核对本地解压目录。';node.classList.remove('hidden');}}
      audio.addEventListener('error',()=>{if(!audio.isConnected)return;const node=audio.parentElement.querySelector('.audio-error');node.textContent='无法播放：本地文件缺失或浏览器无法解码。路径：'+audio.dataset.audioPath;node.classList.remove('hidden');if(state.queue[0]===audio){state.queue.shift();playNext();}});
    });
  }
  function renderContent(){
    if(!state.bundle)return;resetMedia();state.revision++;updateHash();document.querySelectorAll('#tabs button').forEach(button=>{button.classList.toggle('active',button.dataset.tab===state.tab);button.setAttribute('aria-pressed',String(button.dataset.tab===state.tab));});
    const renderers={compare:renderComparison,judge:renderJudges,tools:renderTools,expected:renderExpected,notes:renderNotes};$('content').innerHTML=renderers[state.tab]();hydrateAudio();
  }
  function renderResponse(id,row){
    const run=state.bundle.runs[id],entry=row.systems[id];let content='';
    if(entry.kind==='completed'){
      const turn=entry.turn;const heard=run.audio_judge?.result?.heard_turns?.find(t=>t.user_turn_index===turn.user_turn_index);
      content=`<div class="response-foot">实际第 ${turn.user_turn_index} 轮${turn.routing_label&&turn.routing_label!=='normal'?`<span class="badge warning">${turn.routing_label==='bounded_fallback'?'触发备用澄清':'预设澄清分支'}</span>`:''}</div><p class="response-text">${E(turn.assistant_text||'该轮没有可朗读的回答文字。')}</p>${audioHTML(turn.assistant_audio?.path,state.selected+'-'+row.id+'-'+id,'reply',turn.assistant_audio?.duration_s)}${turn.assistant_audio?.hit_frame_budget?'<p class="audio-error">语音生成触及帧数上限，末尾可能截断。</p>':''}<div class="response-foot">工具 ${turn.tool_events.length} 次 ${turn.tool_events.some(x=>x.response?.ok===false)?'<span class="badge fail">有调用报错</span>':''}</div>`;
      if(turn.input_audio!==row.asset?.path)content+=detail('该系统实际收到的输入',audioHTML(turn.input_audio,state.selected+'-'+id+'-实际输入','user'));
      content+=detail('原文、朗读稿与判官听写',`<span class="text-label">模型原文</span><p>${E(turn.assistant_text)}</p><span class="text-label">数字与单位转换后的朗读稿</span><p>${E(turn.spoken_text)}</p>${turn.asr_text!==null&&turn.asr_text!==undefined?`<span class="text-label">级联系统实际 ASR 转写</span><p>${E(turn.asr_text)}</p>`:''}${heard?`<span class="text-label">判官听到的回答</span><p>${E(heard.assistant_transcript)}</p><span class="text-label">判官声学备注</span><p>${E(heard.acoustic_notes)}</p>`:'<p class="muted">该轮没有单独的判官听写。</p>'}<span class="text-label">实际语音路径</span><p class="file-path">${E(turn.assistant_audio?.path??'无')}</p>`);
      if(turn.tool_events.length)content+=detail('本轮工具调用与返回',turn.tool_events.map((event,i)=>renderToolEvent(event,i+1,'本轮')).join(''));
    }else if(entry.kind==='incomplete'){
      content='<div class="empty-response"><strong>已收到输入，执行中断</strong>没有完成的口头回答；中断前的工具调用仍保留在「工具轨迹」中。</div>';
      if(entry.incomplete.assistant_parts_not_spoken?.length)content+=detail('未朗读的中间文字',`<p class="mini-note">这些文字没有作为完成音频输出，不当作实际语音回复。</p><p>${E(entry.incomplete.assistant_parts_not_spoken.join('\n'))}</p>`);
    }else content=`<div class="empty-response"><strong>${entry.kind==='missing'?'运行文件缺失':'未到达此节点'}</strong>${entry.kind==='missing'?E(state.bundle.errors[id]??'请解压对应的运行记录。'):'该系统没有收到这一轮输入。'}</div>`;
    return `<article class="response-card" data-system="${id}"><div class="model-label">${LABELS[id]}</div>${content}</article>`;
  }
  function renderComparison(){
    return '<p class="section-note">逐轮听实际声音，横向比较三组回复。每列标注实际到达状态；顶部均分与「判官评分」均以整道题为单位。</p>'+C.timeline(state.bundle.testCase,state.bundle.runs).map((row,i)=>`<section class="turn-block" data-node="${E(row.id)}"><div class="turn-header"><div class="turn-heading"><span class="turn-index">${row.supplemental?'补充澄清':`预设第 ${i+1} 轮`} <span class="muted">/ ${E(row.id)}</span></span><button class="button" data-play-row="${E(row.id)}">▶ 依次试听三组回复</button></div><p class="turn-question">${E(row.user_text)}</p><div class="input-line"><span>用户输入语音</span>${audioHTML(row.asset?.path,state.selected+'-'+row.id+'-用户输入','user',row.asset?.duration_s)}</div></div><div class="model-grid response-grid">${SYSTEMS.map(id=>renderResponse(id,row)).join('')}</div>${row.reference?`<div class="reference-box">${detail('查看这一轮的预期结果',`<p class="reference-answer">${E(row.reference.assistant_text)}</p><p class="mini-note">这里列出需要满足的要求；开放题按模型实际创作内容判断，相关只读查询允许。</p>${row.reference.calls.length?raw('参考工具调用与预期返回',row.reference.calls):'<p class="mini-note">本轮参考路径不调用工具。</p>'}`)}</div>`:''}</section>`).join('');
  }
  function renderDiff(before,after,heading='变化前 → 变化后'){
    const differences=C.differences(before,after);if(!differences.length)return '<p class="mini-note">受检状态没有变化。</p>';
    return `<p class="mini-note">${E(heading)} · ${differences.length} 处</p><table class="diff-table"><thead><tr><th>字段</th><th>${heading.startsWith('预期')?'预期':'之前'}</th><th>${heading.startsWith('预期')?'实际':'之后'}</th></tr></thead><tbody>${differences.slice(0,40).map(d=>`<tr><td>${E(d.path)}</td><td>${E(pretty(d.before))}</td><td>${E(pretty(d.after))}</td></tr>`).join('')}</tbody></table>${differences.length>40?raw('全部字段变化',differences):''}`;
  }
  function renderToolEvent(event,index,context){
    const response=event.response??event.expected_response??{};const status=response.status??'unknown';const kind=response.ok===false?'fail':status==='pending'?'warning':response.ok===true?'pass':'pending';
    return `<details class="tool-event"><summary><span class="tool-number">${index.toString().padStart(2,'0')}</span><span>${E(event.call?.tool_name??'未知工具')}</span><span class="badge ${kind}">${E(status)}</span></summary><div class="tool-context">${E(context)} · ${E(response.clock_time??'')} · ${E(event.request_id??response.request_id??'')}</div><span class="text-label">调用参数</span><pre class="tool-args">${E(jsonText(event.call?.arguments??{}))}</pre>${response.error?`<p class="tool-error">${E(response.error.code)}：${E(response.error.message)}</p>`:''}${raw('完整工具返回',response)}${event.state_before&&event.state_after?renderDiff(C.snapshot(event.state_before),C.snapshot(event.state_after)):''}</details>`;
  }
  function renderJudges(){
    const c=state.bundle.testCase;const names=Object.fromEntries(c.evaluation.dimensions.map(d=>[d.id,d.name]));
    return '<p class="section-note">以下为原始判官的整题评分、理由及证据。维度分数是 0–5 分；无可听回答时保留 NA。严格通过还取决于状态检查、权限和执行预算。</p><div class="model-grid judge-grid">'+SYSTEMS.map(id=>{
      const run=state.bundle.runs[id],judge=run?.audio_judge,result=judge?.result;
      let content=`<div class="model-heading"><h3>${LABELS[id]}</h3>${badge(run?.case_pass)}</div>`;
      if(!run)return `<article class="judge-card">${content}<div class="missing-score">本地缺少运行文件。</div></article>`;
      content+=`<p class="judge-meta">${judge?E(judge.requested_model??judge.model)+' · 温度 '+E(judge.temperature):'没有听音评分'}<br>${E(run.judge_status??'unknown')} · 任务完成判断：${run.task_achieved===true?'是':run.task_achieved===false?'否':'NA'}</p>`;
      if(result){content+=result.dimensions.map(d=>`<div class="dimension"><div class="dimension-label"><span>${E(names[d.dimension_id]??d.dimension_id)}</span><strong>${E(d.score)} <small>/ 5</small></strong></div><div class="dimension-bar ${d.score<3?'low':''}"><i style="width:${Math.max(0,Math.min(100,Number(d.score)*20))}%"></i></div><p class="dimension-reason">${E(d.reason)}</p>${(d.evidence??[]).length?detail('查看判官证据',(d.evidence??[]).map(x=>`<div class="evidence">${E(typeof x==='string'?x:jsonText(x))}</div>`).join('')):''}</div>`).join('');
        content+=`<h3 class="details">语义检查</h3>${result.semantic_checks.map(check=>`<div class="check-row"><div class="check-heading">${badge(check.passed,'通过','未通过')}<span class="check-id">${E(check.check_id)}</span></div><p>${E(check.reason)}</p>${(check.evidence??[]).length?detail('证据',check.evidence.map(x=>`<div class="evidence">${E(typeof x==='string'?x:jsonText(x))}</div>`).join('')):''}</div>`).join('')}`;
        content+=detail('严重错误与各轮听写',raw('严重错误',result.critical_failures)+raw('各轮判官听写',result.heard_turns));
      }else content+='<div class="missing-score">此记录没有判官维度分数。执行失败且没有可听回答的题仍计入严格通过率分母。</div>';
      content+=renderRuleChecks(run)+detail('执行信息与评分来源',raw('执行状态',run.execution)+raw('模型解码配置',run.generation)+raw('本版执行与复用来源',run.revision)+raw('判官元数据',judge?Object.fromEntries(Object.entries(judge).filter(([k])=>k!=='result')):null));
      return `<article class="judge-card">${content}</article>`;
    }).join('')+'</div>';
  }
  function renderRuleChecks(run){
    const checks=state.bundle.testCase.evaluation.checks;
    return detail('客观规则检查 · '+run.rule_checks.filter(x=>x.passed).length+'/'+run.rule_checks.length+' 通过',run.rule_checks.map(result=>{
      const check=checks.find(x=>x.id===result.check_id);
      return `<div class="check-row"><div class="check-heading">${badge(result.passed,'通过','未通过')}<span>${E(check?.description??result.check_id)}</span></div><span class="check-id">${E(result.check_id)}</span>${check?.operator==='state_matches'&&result.observed&&result.observed!=='matched'?detail('对比预期与实际状态',renderDiff(check.expected,result.observed,'预期 → 实际')+raw('完整预期',check.expected)+raw('完整实际',result.observed)):raw('检查证据',result.observed)}</div>`;
    }).join(''));
  }
  function renderTools(){
    return '<p class="section-note">显示全过程的实际调用，包括执行中断之前的调用。展开每一步可查看参数、完整返回、报错以及状态变化。</p><div class="model-grid tool-grid">'+SYSTEMS.map(id=>{
      const run=state.bundle.runs[id];if(!run)return `<section class="panel"><h3>${LABELS[id]}</h3><p class="mini-note">本地运行文件缺失。</p></section>`;
      const labels=new Map();run.turns.forEach(t=>t.tool_events.forEach(e=>labels.set(e.request_id,`实际第 ${t.user_turn_index} 轮 / ${t.node_id}`)));
      return `<section class="panel"><div class="model-heading"><h3>${LABELS[id]}</h3><span class="tag">${run.tool_trace.length} 次</span></div>${run.execution.flags.length?`<div class="inline-notice">${E(run.execution.flags.join('；'))}</div>`:''}${run.tool_trace.length?run.tool_trace.map((event,i)=>renderToolEvent(event,i+1,labels.get(event.request_id)??(run.incomplete_turn&&i>=run.incomplete_turn.first_tool_event_index?'中断轮 / '+run.incomplete_turn.node_id:'执行轨迹'))).join(''):'<p class="mini-note">该系统没有调用工具。</p>'}${detail('最终状态与客观检查',raw('最终家庭状态',run.final_state)+renderRuleChecks(run))}</section>`;
    }).join('')+'</div>';
  }
  function renderExpected(){
    const c=state.bundle.testCase,policy=c.evaluation.pass_policy;const lookup=new Map(c.interaction.nodes.map(n=>[n.id,n]));
    return `<p class="section-note">按用户实际要求与已发生的上下文评估。聊天允许相关只读查询；故事、谜底和自选词语不要求照抄示例。写操作逐轮核对对象、字段和值。</p><div class="expected-grid"><div><section class="panel"><h2>逐轮预期结果</h2>${c.reference.turns.map(turn=>`<div class="expected-turn"><h3>${E(turn.node_id)} · ${E(lookup.get(turn.node_id)?.user_text??'')}</h3><span class="text-label">预期约束与说明</span><p class="expected-text">${E(turn.assistant_text)}</p>${turn.calls.length?detail('参考工具路径与预期返回',turn.calls.map((event,i)=>renderToolEvent(event,i+1,'参考路径')).join('')):'<p class="mini-note">参考路径不调用工具。</p>'}${c.evaluation.checks.filter(check=>check.node_id===turn.node_id).map(check=>detail(check.id+' · '+check.description,check.operator==='state_matches'?renderDiff(C.snapshot(c.environment.initial_state),check.expected,'初始状态 → 该轮预期状态')+raw('完整预期状态',check.expected):raw('完整检查标准',check))).join('')}</div>`).join('')}${raw('逐轮允许的查询、写入和语义约束',c.evaluation.behavior_policy)}${raw('允许的其他实现',c.reference.acceptable_alternatives)}</section><section class="panel"><h2>整题通过条件</h2><ul class="policy-list"><li>执行正常结束，遵守用户轮数、工具次数和生成预算。</li><li>全部必需客观检查与语义检查通过。</li><li>没有严重错误，语音生成没有触及失败预算。</li>${policy.min_applicable_dimension_score!==null&&policy.min_applicable_dimension_score!==undefined?`<li>六个评分维度分别至少 ${E(policy.min_applicable_dimension_score)} 分。</li>`:'<li>维度均分另外报告，不单独作为工具题通过线。</li>'}</ul>${raw('该题全部检查项',c.evaluation.checks)}${raw('严重错误定义',c.evaluation.critical_failure_definitions)}</section></div><div><section class="panel"><h2>六维评分标准</h2>${c.evaluation.dimensions.map(d=>`<div class="rubric-row"><strong>${E(d.name)}</strong><p>${E(d.criterion)}</p>${detail('展开 0–5 分锚点',`<table class="anchors">${Object.entries(d.anchors).map(([score,text])=>`<tr><td>${E(score)} 分</td><td>${E(text)}</td></tr>`).join('')}</table>`)}</div>`).join('')}</section><section class="panel"><h2>家庭环境与执行约束</h2><div class="budget-grid"><span><strong>${c.interaction.budget.max_user_turns} 轮</strong>最多用户交互</span><span><strong>${c.interaction.budget.max_tool_calls} 次</strong>最多工具调用</span><span><strong>${c.interaction.budget.context_window_tokens}</strong>上下文 token 上限</span><span><strong>${c.interaction.budget.max_consecutive_tool_calls} 次</strong>最多连续工具调用</span></div>${raw('可信身份与系统要求',c.model_context)}${raw('完整初始家庭状态',c.environment.initial_state)}${raw('故障与权限夹具',Object.fromEntries(Object.entries(c.environment).filter(([k])=>k!=='initial_state')))}${raw('对话节点与澄清策略',c.interaction)}<div class="source-links"><button class="button" data-download="data/cases/${E(state.selected)}.json">下载原始题目 JSON</button>${SYSTEMS.map(id=>`<button class="button" data-download="runs/${id}/${E(state.selected)}.json">${id==='edge_native'?'实验组':id==='qwen35_2b'?'2B':'4B'} 原始记录</button>`).join('')}</div></section></div></div>`;
  }
  function noteRecord(){return state.notes[state.selected]??C.blankNote(state.selected);}
  function renderNotes(){
    const note=noteRecord();return `<section class="panel"><div class="notes-intro"><div><h2>人工评审记录</h2><p class="mini-note">记录你听到的问题、对判官结论的意见和需要复查的内容。</p></div><span class="badge ${note.done?'pass':'pending'}">${note.done?'已听完':'尚未听完'}</span></div><label class="field-label" for="case-note">整题备注</label><textarea id="case-note" class="note-area" data-note-field="case" maxlength="20000" placeholder="例如：第二轮数字读法不清晰；需要复核判官对工具错误的解释。">${E(note.note)}</textarea><div class="save-status" id="save-status">${note.updated_at&&state.notes[state.selected]?'上次保存：'+E(new Date(note.updated_at).toLocaleString()):'输入后自动保存在当前浏览器'}</div><div class="model-grid note-systems">${SYSTEMS.map(id=>{const value=note.systems[id]??{opinion:'pending',note:''};return `<div><h3>${LABELS[id]}</h3><label class="field-label" for="opinion-${id}">对原判定的意见</label><select id="opinion-${id}" data-note-system="${id}" data-note-kind="opinion">${[['pending','尚未判断'],['agree','同意原判定'],['disagree','不同意原判定'],['check','需要进一步复核']].map(([key,label])=>`<option value="${key}" ${key===value.opinion?'selected':''}>${label}</option>`).join('')}</select><textarea class="note-area" aria-label="${E(LABELS[id])}人工备注" data-note-system="${id}" data-note-kind="note" maxlength="20000" placeholder="语音、内容、工具操作或评分方面的观察…">${E(value.note)}</textarea></div>`;}).join('')}</div><p class="mini-note">人工记录与正式评分分别保存。导出 JSON 可恢复评审进度；CSV 适合放入 Excel 汇总。不同浏览器的自动保存空间不同，建议及时导出备份。</p></section>`;
  }
  function exportObject(){return {format:'homevoice-human-review-v1',dataset_key:state.key,manifest_sha256:state.index.manifest_sha256,exported_at:new Date().toISOString(),records:Object.values(state.notes).sort((a,b)=>a.case_id.localeCompare(b.case_id))};}
  function persist(){try{localStorage.setItem(state.key,JSON.stringify(exportObject()));if($('save-status'))$('save-status').textContent='已自动保存 · '+new Date().toLocaleTimeString();}catch(_error){toast('浏览器未能自动保存，请立即导出 JSON 备份。');if($('save-status'))$('save-status').textContent='自动保存失败，请导出备份';}}
  function updateNote(change){if(!state.selected)return;const note=noteRecord();change(note);note.updated_at=new Date().toISOString();state.notes[state.selected]=note;persist();renderHeading();applyFilters();}
  function downloadBlob(blob,name){const url=URL.createObjectURL(blob);const anchor=document.createElement('a');anchor.href=url;anchor.download=name;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),15000);}
  function exportNotes(format){
    if(!state.index)return;
    const date=new Date().toISOString().slice(0,10);if(format==='json'){downloadBlob(new Blob([JSON.stringify(exportObject(),null,2)],{type:'application/json'}),'人工评审-'+date+'.json');return;}
    const rows=[['题号','题目','类别','已听完','需复核','系统','人工意见','系统备注','整题备注','更新时间']];
    for(const note of Object.values(state.notes)){const c=state.cases.get(note.case_id);for(const id of SYSTEMS){const value=note.systems[id]??{opinion:'pending',note:''};rows.push([note.case_id,c?.title,c?.category,note.done?'是':'否',note.flag?'是':'否',id,({pending:'尚未判断',agree:'同意原判定',disagree:'不同意原判定',check:'需复核'})[value.opinion],value.note,note.note,note.updated_at]);}}
    downloadBlob(new Blob(['\ufeff'+rows.map(row=>row.map(C.csvCell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),'人工评审-'+date+'.csv');
  }
  async function importNotes(file){
    if(!state.index){toast('请先连接数据目录。');return;}if(file.size>10*1024*1024){toast('评审记录文件超过 10 MB。');return;}
    try{const rows=C.parseReviewImport(JSON.parse(await file.text()),state.key,new Set(state.cases.keys()));let changed=0;for(const row of rows){const previous=state.notes[row.case_id];if(!previous||Date.parse(row.updated_at)>Date.parse(previous.updated_at)){state.notes[row.case_id]=row;changed++;}}persist();applyFilters();renderHeading();if(state.tab==='notes')renderContent();toast('导入 '+changed+' 道题的记录；同题保留更新时间较新的版本。');}catch(error){toast('未导入：'+error.message);}
  }
  function playNext(){if(!state.queue.length)return;state.queue[0].play().catch(()=>{state.queue=[];toast('浏览器未能自动连续播放，请点击对应语音的播放按钮。');});}
  document.addEventListener('play',event=>{if(event.target.tagName!=='AUDIO')return;document.querySelectorAll('audio').forEach(a=>{if(a!==event.target)a.pause();});event.target.playbackRate=state.speed;if(state.queue.length&&state.queue[0]!==event.target)state.queue=[];},true);
  document.addEventListener('ended',event=>{if(event.target===state.queue[0]){state.queue.shift();playNext();}},true);
  function navigate(delta){const at=state.filtered.findIndex(x=>x.case_id===state.selected),next=at+delta;if(at>=0&&next>=0&&next<state.filtered.length){state.page=Math.floor(next/state.pageSize);selectCase(state.filtered[next].case_id);window.scrollTo({top:0,behavior:'instant'});}}
  document.addEventListener('click',async event=>{
    const button=event.target.closest('button');if(!button)return;
    if(button.dataset.case){selectCase(button.dataset.case);return;}
    if(button.dataset.category){state.filters.category=button.dataset.category;document.querySelectorAll('#category-filter button').forEach(b=>b.classList.toggle('selected',b===button));state.page=0;applyFilters();return;}
    if(button.dataset.tab){state.tab=button.dataset.tab;renderContent();return;}
    if(button.dataset.nav){navigate(Number(button.dataset.nav));return;}
    if(button.dataset.noteAction){const field=button.dataset.noteAction;updateNote(note=>note[field]=!note[field]);if(state.tab==='notes')renderContent();return;}
    if(button.dataset.playRow){stopAudio();const section=button.closest('.turn-block');state.queue=Array.from(section.querySelectorAll('audio[data-role=reply]')).filter(a=>a.src);if(!state.queue.length)toast('这一轮没有可播放的完成音频。');else playNext();return;}
    if(button.dataset.download){try{const path=button.dataset.download;const parts=path.split('/');const filename=button.dataset.filename??(parts[0]==='runs'?parts[1]+'-'+parts.at(-1):parts.at(-1));downloadBlob(await state.source.file(path),filename);}catch(error){toast(error.message);}return;}
  });
  document.addEventListener('input',event=>{
    const target=event.target;
    if(target.id==='search'){state.filters.search=target.value;state.page=0;applyFilters();}
    if(target.dataset.noteField==='case')updateNote(note=>note.note=target.value);
    if(target.dataset.noteSystem&&target.dataset.noteKind==='note')updateNote(note=>{const id=target.dataset.noteSystem;note.systems[id]??={opinion:'pending',note:''};note.systems[id].note=target.value;});
  });
  document.addEventListener('change',event=>{
    const target=event.target;const filterIds={'scene-filter':'scene','turn-filter':'turns','review-filter':'review','result-filter':'result',sort:'sort'};
    if(filterIds[target.id]){state.filters[filterIds[target.id]]=target.value;state.page=0;applyFilters();}
    if(target.dataset.noteSystem&&target.dataset.noteKind==='opinion')updateNote(note=>{const id=target.dataset.noteSystem;note.systems[id]??={opinion:'pending',note:''};note.systems[id].opinion=target.value;});
  });
  $('open-folder').addEventListener('click',pickFolder);$('welcome-open').addEventListener('click',pickFolder);
  $('list-prev').addEventListener('click',()=>{state.page--;renderList();$('case-list').scrollTop=0;});$('list-next').addEventListener('click',()=>{state.page++;renderList();$('case-list').scrollTop=0;});
  $('speed').addEventListener('change',event=>{state.speed=Number(event.target.value);document.querySelectorAll('audio').forEach(audio=>audio.playbackRate=state.speed);});
  $('export-json').addEventListener('click',()=>exportNotes('json'));$('export-csv').addEventListener('click',()=>exportNotes('csv'));
  $('import-notes').addEventListener('click',()=>{if(!state.index){toast('请先选择数据目录。');return;}$('import-file').click();});$('import-file').addEventListener('change',event=>{if(event.target.files[0])importNotes(event.target.files[0]);event.target.value='';});
  document.addEventListener('keydown',event=>{if(event.altKey&&['ArrowLeft','ArrowRight'].includes(event.key)&&!['INPUT','TEXTAREA','SELECT'].includes(event.target.tagName)){event.preventDefault();navigate(event.key==='ArrowRight'?1:-1);}});
  window.addEventListener('beforeunload',()=>{resetMedia();});
  if(['127.0.0.1','localhost'].includes(location.hostname)&&location.protocol==='http:')connect(new HttpSource());else{$('source-label').textContent='本地文件模式';$('welcome').classList.remove('hidden');}
})();
