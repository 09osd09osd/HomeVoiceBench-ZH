// Semantic alignment and local review record integrity, without a DOM dependency.
const assert = require('node:assert/strict');
const test = require('node:test');
const C = require('../review/core.js');

test('missing judge score stays NA; a real zero remains zero', () => {
  assert.equal(C.meanScore({audio_judge:null}), null);
  assert.equal(C.meanScore({audio_judge:{result:{dimensions:[{score:0},{score:null}]}}}), 0);
  assert.equal(C.meanScore({audio_judge:{result:{dimensions:[{score:2},{score:4}]}}}), 3);
});
test('alignment separates completed audio, interrupted input and never reached nodes', () => {
  const c = {interaction:{nodes:[{id:'U1'},{id:'U2'},{id:'U3'}],clarification:{fallback_text:'请再说一次'}},variants:[{modality:'audio',audio_assets:[{node_id:'U2',path:'x'}]}],reference:{turns:[]}};
  const runs = {edge_native:{turns:[{node_id:'U1'}],incomplete_turn:{node_id:'U2',assistant_parts_not_spoken:['没有朗读']}},qwen35_2b:{turns:[{node_id:'U1'},{node_id:'U2'},{node_id:'FALLBACK'}]}};
  const rows=C.timeline(c,runs);
  assert.deepEqual(rows.map(x=>x.id),['U1','U2','U3','FALLBACK']);
  assert.equal(rows[0].systems.edge_native.kind,'completed');
  assert.equal(rows[1].systems.edge_native.kind,'incomplete');
  assert.equal(rows[1].systems.edge_native.turn,undefined);
  assert.equal(rows[1].asset.path,'x');
  assert.equal(rows[2].systems.edge_native.kind,'unreached');
  assert.equal(rows[0].systems.qwen35_4b.kind,'missing');
  assert.equal(rows[3].supplemental,true);
  assert.equal(C.timeline(c,{}).length,3);
});
test('filters distinguish missing scores, strict failures and execution failures', () => {
  const cases=[{case_id:'C01_001',category:'chat',scene_id:'C01',turn_count:1,title:'安慰',user_texts:['今天有点难过']},{case_id:'T01_001',category:'tool',scene_id:'T01',turn_count:2,title:'灯光',user_texts:[]}];
  const map=new Map([['edge_native/C01_001',{case_pass:true,mean_score:4,judged:true,execution_status:'completed'}],['qwen35_2b/C01_001',{case_pass:false,mean_score:2,judged:true,execution_status:'completed'}],['edge_native/T01_001',{case_pass:false,mean_score:null,judged:false,execution_status:'failed'}]]);
  const base={category:'all',scene:'all',turns:'all',review:'all',result:'all',sort:'id'};
  const ids=filters=>C.filterCases(cases,map,{'C01_001':{done:true,flag:true}},{...base,...filters}).map(x=>x.case_id);
  assert.deepEqual(ids({result:'disagreement'}),['C01_001']);
  assert.deepEqual(ids({result:'any_unjudged'}),['T01_001']);
  assert.deepEqual(ids({result:'any_failed'}),['T01_001']);
  assert.deepEqual(ids({review:'todo'}),['T01_001']);
  assert.deepEqual(ids({review:'flag',search:'难过'}),['C01_001']);
  assert.deepEqual(ids({category:'tool',turns:'2'}),['T01_001']);
  assert.deepEqual(ids({sort:'edge_low'}),['C01_001','T01_001']);
});
test('state changes keep real device deltas and omit advancing clock', () => {
  const before={clock_time:'10:00',devices:[{id:'light',state:{power:false,brightness_pct:20}}]};
  const after={clock_time:'10:01',devices:[{id:'light',state:{power:true,brightness_pct:20}}]};
  assert.deepEqual(C.differences(C.snapshot(before),C.snapshot(after)),[{path:'devices.light.power',before:false,after:true}]);
  assert.deepEqual(C.differences({}, {scheduled:[]}),[{path:'scheduled',before:undefined,after:[]}]);
});
test('only explicit dataset and audio paths are readable', () => {
  for(const path of ['data/cases/T06_003.json','runs/edge_native/C01_001.json','assets/audio/edge/abcdef123.wav','assets/audio/baseline/abcdef123.wav','reports/summary.json'])assert.equal(C.safePath(path),true,path);
  for(const path of ['.local/keys.json','../reports/summary.json','data/cases/../../.local/keys.json','https://example.org/a.wav','data/cases/C01_001.json\n','assets\\audio\\edge\\abc.wav','reports/summary.json?x=1'])assert.equal(C.safePath(path),false,path);
  assert.equal(C.escapeHTML('<img src=x onerror="bad">&\''),'&lt;img src=x onerror=&quot;bad&quot;&gt;&amp;&#39;');
});
test('review imports preserve origin, reject duplicates and strip unknown fields', () => {
  const row={...C.blankNote('C01_001'),note:'听完第一轮',untrusted_extra:'ignored',systems:{edge_native:{opinion:'check',note:'声音不清楚'}}};
  const input={format:'homevoice-human-review-v1',dataset_key:'frozen-hash',records:[row]};const known=new Set(['C01_001']);
  const restored=C.parseReviewImport(input,'frozen-hash',known);
  assert.equal(restored[0].note,row.note);assert.equal(restored[0].untrusted_extra,undefined);
  assert.throws(()=>C.parseReviewImport(input,'other-hash',known));
  assert.throws(()=>C.parseReviewImport({...input,records:[row,row]},'frozen-hash',new Set(['C01_001','C01_002'])));
  assert.throws(()=>C.parseReviewImport({...input,records:[{...row,case_id:'unknown'}]},'frozen-hash',known));
  assert.throws(()=>C.validateNote({...row,systems:{edge_native:{opinion:'replace_score',note:''}}},known));
  assert.throws(()=>C.validateNote({...row,updated_at:'invalid'},known));
});
test('spreadsheet export escapes quotes and prevents notes becoming formulas', () => {
  assert.equal(C.csvCell('=HYPERLINK("x")'),'"\'=HYPERLINK(""x"")"');
  assert.equal(C.csvCell('  +123'),'"\'  +123"');
  assert.equal(C.csvCell('第一行\n第二行'),'"第一行\n第二行"');
});
