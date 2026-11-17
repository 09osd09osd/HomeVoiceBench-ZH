(function (root) {
  'use strict';
  const SYSTEMS = ['edge_native', 'qwen35_2b', 'qwen35_4b'];
  const LABELS = {edge_native:'实验组 · EdgeInstant', qwen35_2b:'Baseline · Qwen 2B', qwen35_4b:'Baseline · Qwen 4B'};
  const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safePath = path => typeof path === 'string' && /^(?:reports\/(?:summary|case_overview|scene_overview|run_overview)\.json|data\/manifest\.json|data\/cases\/[TC]\d{2}_\d{3}\.json|runs\/(?:edge_native|qwen35_2b|qwen35_4b)\/[TC]\d{2}_\d{3}\.json|assets\/audio\/(?:input|edge|baseline)\/[a-f0-9]+\.wav)(?![\s\S])/.test(path);
  const meanScore = run => {
    const values = (run?.audio_judge?.result?.dimensions ?? []).map(x => x.score).filter(Number.isFinite);
    return values.length ? values.reduce((a,b)=>a+b,0)/values.length : null;
  };
  const snapshot = state => {
    if (!state) return {};
    return {devices:Array.isArray(state.devices) ? Object.fromEntries(state.devices.map(x=>[x.id,x.state])) : (state.devices??{}), schedules:state.schedules??[],playbacks:state.playbacks??[],tasks:state.tasks??[]};
  };
  function differences(before, after, prefix='', result=[]) {
    if (JSON.stringify(before) === JSON.stringify(after)) return result;
    if (before !== null && after !== null && typeof before==='object' && typeof after==='object') {
      for (const key of new Set([...Object.keys(before),...Object.keys(after)])) differences(before[key],after[key],prefix ? prefix+'.'+key : key,result);
    } else result.push({path:prefix,before,after});
    return result;
  }
  function timeline(testCase, runs) {
    const rows = testCase.interaction.nodes.map(node=>({...node, supplemental:false}));
    if (SYSTEMS.some(id=>(runs[id]?.turns??[]).some(t=>t.node_id==='FALLBACK') || runs[id]?.incomplete_turn?.node_id==='FALLBACK')) {
      rows.push({id:'FALLBACK',user_text:testCase.interaction.clarification.fallback_text,supplemental:true});
    }
    const assets = testCase.variants.find(v=>v.modality==='audio')?.audio_assets ?? [];
    return rows.map(node=>({...node,asset:assets.find(a=>a.node_id===node.id),reference:testCase.reference.turns.find(t=>t.node_id===node.id),systems:Object.fromEntries(SYSTEMS.map(id=>{
      const run = runs[id];
      const turn = run?.turns?.find(t=>t.node_id===node.id);
      const incomplete = run?.incomplete_turn?.node_id===node.id ? run.incomplete_turn : null;
      return [id,turn ? {kind:'completed',turn} : incomplete ? {kind:'incomplete',incomplete} : {kind:run?'unreached':'missing'}];
    }))}));
  }
  function filterCases(rows, runMap, notes, filters) {
    const needle = (filters.search??'').trim().toLowerCase();
    const result = rows.filter(c=>{
      if (needle && ![c.case_id,c.title,c.scene_id,...(c.user_texts??[])].join(' ').toLowerCase().includes(needle)) return false;
      if (filters.category!=='all' && c.category!==filters.category) return false;
      if (filters.scene!=='all' && c.scene_id!==filters.scene) return false;
      if (filters.turns!=='all' && c.turn_count!==Number(filters.turns)) return false;
      const note=notes[c.case_id];
      if (filters.review==='done' && !note?.done || filters.review==='todo' && note?.done || filters.review==='flag' && !note?.flag) return false;
      const rr=SYSTEMS.map(id=>runMap.get(id+'/'+c.case_id));const edge=rr[0];
      if (filters.result==='edge_pass' && edge?.case_pass!==true || filters.result==='edge_fail' && edge?.case_pass!==false) return false;
      if (filters.result==='any_failed' && !rr.some(r=>r?.execution_status==='failed')) return false;
      if (filters.result==='any_unjudged' && !rr.some(r=>r && !r.judged)) return false;
      if (filters.result==='disagreement' && new Set(rr.map(r=>r?.case_pass).filter(x=>typeof x==='boolean')).size<2) return false;
      return true;
    });
    const score = c => runMap.get('edge_native/'+c.case_id)?.mean_score;
    const spread = c => {const scores=SYSTEMS.map(id=>runMap.get(id+'/'+c.case_id)?.mean_score).filter(Number.isFinite);return scores.length>1?Math.max(...scores)-Math.min(...scores):-1;};
    result.sort((a,b)=>{
      if (filters.sort==='edge_low') {const av=score(a),bv=score(b);const delta=(Number.isFinite(av)?av:Infinity)-(Number.isFinite(bv)?bv:Infinity);if(delta && !Number.isNaN(delta))return delta;}
      if (filters.sort==='difference') {const delta=spread(b)-spread(a);if(delta)return delta;}
      return a.case_id.localeCompare(b.case_id);
    });
    return result;
  }
  function blankNote(caseId) {return {case_id:caseId,done:false,flag:false,note:'',systems:{},updated_at:new Date().toISOString()};}
  function validateNote(row, caseIds) {
    if (!row || !caseIds.has(row.case_id) || typeof row.done!=='boolean' || typeof row.flag!=='boolean' || typeof row.note!=='string' || row.note.length>20000 || !Number.isFinite(Date.parse(row.updated_at))) throw Error('人工记录含有无效题号、状态或备注。');
    const clean={case_id:row.case_id,done:row.done,flag:row.flag,note:row.note,systems:{},updated_at:row.updated_at};
    for (const [id,value] of Object.entries(row.systems??{})) {
      if (!SYSTEMS.includes(id) || !value || !['pending','agree','disagree','check'].includes(value.opinion) || typeof value.note!=='string' || value.note.length>20000) throw Error('人工记录的模型意见格式不正确。');
      clean.systems[id]={opinion:value.opinion,note:value.note};
    }
    return clean;
  }
  function parseReviewImport(value, datasetKey, caseIds) {
    if (!value || value.format!=='homevoice-human-review-v1' || value.dataset_key!==datasetKey || !Array.isArray(value.records) || value.records.length>caseIds.size) throw Error('这份评审记录不属于当前数据集或版本。');
    const rows=value.records.map(row=>validateNote(row,caseIds));
    if(new Set(rows.map(r=>r.case_id)).size!==rows.length)throw Error('导入文件包含重复题号。');
    return rows;
  }
  function csvCell(value) {
    let text=String(value??'');if (/^\s*[=+\-@]/.test(text))text="'"+text;
    return '"'+text.replaceAll('"','""')+'"';
  }
  const api={SYSTEMS,LABELS,escapeHTML,safePath,meanScore,snapshot,differences,timeline,filterCases,blankNote,validateNote,parseReviewImport,csvCell};
  if(typeof module==='object'&&module.exports)module.exports=api;else root.ReviewCore=api;
})(typeof globalThis!=='undefined'?globalThis:this);
