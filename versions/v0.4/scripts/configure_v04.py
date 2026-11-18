"""One-time source migration; initialize either isolated dataset workspace."""
import argparse,copy,json,re,shutil,sys
from pathlib import Path
CODE=Path(__file__).resolve().parents[1]
def migrate():
    if json.loads((CODE/'spec/sandbox.json').read_text('utf-8')).get('schema_version')=='0.4.0':return
    marker=CODE/'.configured'
    if marker.exists():return
    shutil.copy2(CODE/'homevoice/blueprints.py',CODE/'homevoice/legacy_blueprints.py')
    for p in (CODE/'homevoice').glob('*.py'):
        if p.name=='paths.py':continue
        s=p.read_text('utf-8')
        s=re.sub(r'ROOT\s*=\s*Path\(__file__\)\.resolve\(\)\.parents\[1\]', 'from .paths import ROOT,SHARED_ROOT',s)
        if p.name=='cloud.py':
            s=s.replace("override=ROOT/'.local/keys.json'","override=SHARED_ROOT/'.local/keys.json'").replace("p = ROOT/'.local/cloud.json'","p = SHARED_ROOT/'.local/cloud.json'").replace('HomeVoiceBench-ZH/0.3','HomeVoiceBench-ZH/0.4')
        if p.name=='authorization.py':s=s.replace("'home_get','clock_get','policy_get','device_list','device_get'","'device_query'").replace('turn_scoped_authorization_v0.3','turn_scoped_authorization_v0.4')
        if p.name=='revision.py':s=s.replace("'benchmark_version':'0.3.0'","'benchmark_version':'0.4.0'")
        p.write_text(s,'utf-8')
    for p in (CODE/'scripts').glob('*.py'):
        if p.name=='configure_v04.py':continue
        s=p.read_text('utf-8')
        s=s.replace('sys.path.insert(0,str(ROOT))','sys.path.insert(0,str(Path(__file__).resolve().parents[1]))')
        if re.search(r'ROOT\s*=\s*Path\(__file__\)\.resolve\(\)\.parents\[1\]',s):
            s=s.replace('from pathlib import Path','from pathlib import Path\nimport sys\nsys.path.insert(0,str(Path(__file__).resolve().parents[1]))')
            s=re.sub(r'ROOT\s*=\s*Path\(__file__\)\.resolve\(\)\.parents\[1\]','from homevoice.paths import ROOT,SHARED_ROOT',s)
        if p.name=='launch_qwen.py':
            s=s.replace("ROOT/'runtime/llama-b11552/llama-server.exe'","SHARED_ROOT/'runtime/llama-b11552/llama-server.exe'").replace("ROOT/'models'","SHARED_ROOT/'models'").replace('model.relative_to(ROOT)','model.relative_to(SHARED_ROOT)').replace('cwd=ROOT','cwd=SHARED_ROOT')
        p.write_text(s,'utf-8')
    path=CODE/'spec/sandbox.json';spec=json.loads(path.read_text('utf-8'));old={t['name']:t for t in spec['tools']}
    query=copy.deepcopy(old['device_list']);query.update(name='device_query',description='查询设备。可按房间ID或中文房间名、设备类型、设备ID或完整中文设备名筛选；一次返回设备ID、状态、能力、当前用户权限及正在播放的会话。省略筛选返回全部可见设备。未知房间明确报错。')
    query['input_schema']={'type':'object','properties':{'room_id':{'type':'string','description':'可选：房间ID或中文房间名，例如study或书房。'},'device_type':{'type':'string','description':'可选：light/air_conditioner/curtain/fan/purifier/speaker/tv/vacuum。'},'device_id':{'type':'string','description':'可选：设备ID或唯一完整中文设备名。'}},'required':[],'additionalProperties':False}
    query['output_schema']={'type':'object','properties':{'request_id':{'type':'string'},'ok':{'type':'boolean'},'status':{'type':'string'},'data':{'type':['object','null']},'error':{'type':['object','null']},'operation_id':{'type':['string','null']},'clock_time':{'type':'string'}},'required':['request_id','ok','status','data','error','operation_id','clock_time'],'additionalProperties':False}
    spec['tools']=[query]+[old[n] for n in ['device_set','sensor_read','schedule_list','schedule_create','schedule_update','schedule_cancel','media_search','media_play','media_control','task_get','task_cancel']]
    spec.update(schema_version='0.4.0',core_tool_names=[t['name'] for t in spec['tools'][:10]],extension_tool_names=['task_get','task_cancel'])
    path.write_text(json.dumps(spec,ensure_ascii=False,indent=2),'utf-8')
    p=CODE/'spec/case.schema.json';schema=json.loads(p.read_text('utf-8'))
    schema['properties']['schema_version']={'type':'string','const':'0.4.0'}
    schema['properties']['design']={'type':'object','description':'Versioned split, family, difficulty progression and independent fact-check specification.'}
    p.write_text(json.dumps(schema,ensure_ascii=False,indent=2),'utf-8')
    p=CODE/'spec/evaluation_profiles.json';profile=json.loads(p.read_text('utf-8'));profile['schema_version']='0.4.0'
    profile['qwen_baselines']['generation'].update(temperature=0,top_p=1,top_k=1,min_p=0,presence_penalty=0,frequency_penalty=0,repeat_penalty=1)
    profile['qwen_baselines']['decoding_policy']='user_requested_greedy_content_and_tools_v0.4'
    profile['reporting']='Independent pilot100 and benchmark1000; task pass separate from six dimension quality; no best-answer selection.'
    profile['dialogue_router']['version']='fixed_purposeful_nodes_v0.4'
    p.write_text(json.dumps(profile,ensure_ascii=False,indent=2),'utf-8')
    marker.write_text('source migration complete\n','utf-8')
def initialize(split):
    target=CODE/('pilot' if split=='development' else 'benchmark')
    for d in ['data/cases','data/audio','data/authoring','reports','runs','logs','assets/audio','spec','review','outputs']:(target/d).mkdir(parents=True,exist_ok=True)
    for d in ['spec','review']:
        for p in (CODE/d).rglob('*'):
            if p.is_file():
                q=target/d/p.relative_to(CODE/d);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
    print(json.dumps({'root':str(target),'split':split},ensure_ascii=False))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--split',choices=['development','test'],default='development');a=ap.parse_args();migrate();initialize(a.split)
