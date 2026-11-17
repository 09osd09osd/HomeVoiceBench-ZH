"""Deterministic, case-isolated home sandbox. No real appliances or outside I/O."""
import copy,json
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from jsonschema import Draft202012Validator,FormatChecker
from referencing import Registry,Resource
ROOT=Path(__file__).resolve().parents[1]
TYPES=json.loads((ROOT/'spec/types.schema.json').read_text('utf-8'))
CATALOG=json.loads((ROOT/'spec/sandbox.json').read_text('utf-8'))
TOOLS={x['name']:x for x in CATALOG['tools']}
VERSION='household_sandbox_v0.3'
REGISTRY=Registry().with_resource(TYPES['$id'],Resource.from_contents(TYPES))
def validate(data,schema): Draft202012Validator(schema,registry=REGISTRY,format_checker=FormatChecker()).validate(data)
def dt(s): return datetime.fromisoformat(s)
def cp(x): return copy.deepcopy(x)
def compact_tools():
    def expand(s):
        if isinstance(s,list):return [expand(x) for x in s]
        if not isinstance(s,dict):return s
        if '$ref' in s:return expand(TYPES['$defs'][s['$ref'].split('/')[-1]])
        return {k:expand(v) for k,v in s.items() if k not in ('description',)}
    return [{'type':'function','function':{'name':t['name'],'description':t['description'],'parameters':expand(t['input_schema'])}} for t in TOOLS.values()]
class Failure(Exception):
    def __init__(self,code,message,retryable=False):self.code,self.message,self.retryable=code,message,retryable

class Sandbox:
    def __init__(self,environment,actor):
        validate(environment,{'$ref':TYPES['$id']+'#/$defs/Fixture'})
        self.fixture=cp(environment);self.state=cp(environment['initial_state']);self.initial=cp(self.state);self.actor=cp(actor)
        self.now=dt(self.state['clock']['current_at']);self.trace=[];self.snapshots=[cp(self.state)];self.checkpoints={};self.cache={};self.attempts={};self.jobs={};self.fired=set();self.seq={}
        self.current_node_id=None;self.current_user_turn_index=0;self.turn_ranges=[];self.turn_start=0
    def begin_turn(self,node_id,user_turn_index=None):
        self.current_node_id=node_id
        self.current_user_turn_index=user_turn_index or len(self.turn_ranges)+1
        self.turn_start=len(self.trace)
    def stamp(self):return self.now.isoformat(timespec='milliseconds')
    def new_id(self,prefix):
        self.seq[prefix]=self.seq.get(prefix,0)+1
        return f'{prefix}_{self.fixture["id_prefix"]}_{self.seq[prefix]:03d}'
    def find(self,collection,key):
        v=next((x for x in self.state[collection] if x['id']==key),None)
        if v is None:raise Failure('NOT_FOUND','指定对象不存在或不可见。')
        return v
    def allowed(self,kind,key,action,owner=None):
        rules=[r for r in self.fixture['permissions'] if r['actor_role'] in (self.actor['role'],'*') and r['resource_type']==kind and (key in r['resource_ids'] or '*' in r['resource_ids']) and (action in r['actions'] or '*' in r['actions']) and (not r['owner_only'] or owner==self.actor['id'])]
        return any(r['decision']=='allow' for r in rules) and not any(r['decision']=='deny' for r in rules)
    def permit(self,kind,key,action,owner=None):
        if not self.allowed(kind,key,action,owner):raise Failure('PERMISSION_DENIED','当前用户没有此操作权限。')
    def owned(self,collection,key,kind,action):
        v=self.find(collection,key);self.permit(kind,key,action,v.get('owner_id'));return v
    def device_changes(self,key,changes,action='device_set'):
        d=self.find('devices',key);self.permit('device',key,action)
        if not d['online']:raise Failure('DEVICE_OFFLINE','设备离线。',True)
        caps={c['field']:c for c in d['capabilities']}
        for k,v in changes.items():
            if k not in caps:raise Failure('UNSUPPORTED_OPERATION',f'设备不支持字段 {k}。')
            c=caps[k]
            if c['allowed_values'] is not None and v not in c['allowed_values']:raise Failure('OUT_OF_RANGE',f'{k} 不在允许取值中。')
            if c['minimum'] is not None and v<c['minimum'] or c['maximum'] is not None and v>c['maximum']:raise Failure('OUT_OF_RANGE',f'{k} 超出范围。')
            if k=='target_room_ids' and any(r not in [x['id'] for x in self.state['home']['rooms']] for r in v):raise Failure('NOT_FOUND','目标房间不存在。')
            if k=='cleaning_action':
                current=d['state']['cleaning_status'];valid={'start':['idle','charging'],'pause':['cleaning'],'resume':['paused'],'return_home':['idle','cleaning','paused']}
                if current not in valid[v]:raise Failure('CONFLICT','清扫状态不支持此操作。')
        return d
    def apply_device(self,d,changes):
        for k,v in changes.items():
            if k=='cleaning_action':d['state']['cleaning_status']={'start':'cleaning','pause':'paused','resume':'cleaning','return_home':'returning'}[v]
            else:d['state'][k]=cp(v)
    def next_time(self,when,after):
        if when['timezone']!=self.state['clock']['timezone']:raise Failure('INVALID_TIME','安排时区与家庭时区不符。')
        if when['mode']=='once':return dt(when['at'])
        # Fixture uses Asia/Taipei (+08:00, no DST); no dependence on machine timezone.
        if when['timezone']!='Asia/Taipei':raise Failure('INVALID_TIME','此版本夹具只接受 Asia/Taipei。')
        hh,mm,ss=map(int,when['local_time'].split(':'))
        for day in range(8):
            t=(after+timedelta(days=day)).replace(hour=hh,minute=mm,second=ss,microsecond=0)
            if t>after and (when['mode']=='daily' or t.isoweekday() in when['weekdays']):return t
        raise Failure('INVALID_TIME','无法确定下一次触发时间。')
    def check_schedule(self,kind,when,payload):
        validate({'kind':kind,'when':when,'payload':payload},TOOLS['schedule_create']['input_schema'])
        if self.next_time(when,self.now)<=self.now:raise Failure('INVALID_TIME','一次性安排必须位于未来。')
        if kind=='alarm':
            d=self.find('devices',payload['target_device_id']);self.permit('device',d['id'],'media_play')
            if d['type'] not in ('speaker','tv'):raise Failure('UNSUPPORTED_OPERATION','该设备不能播放闹钟。')
        if kind=='device_action':
            for a in payload['actions']:self.device_changes(a['device_id'],a['changes'])
    def _dispatch(self,name,a,fault=None):
        if name=='home_get':self.permit('home',self.state['home']['home_id'],name);return self.state['home']
        if name=='clock_get':return {'now':self.stamp(),'timezone':self.state['clock']['timezone']}
        if name=='policy_get':
            owner=self.actor['id'] if a['resource_id']=='self' else next((v.get('owner_id') for col in ['schedules','tasks','playbacks'] for v in self.state[col] if v['id']==a['resource_id']),None)
            yes=self.allowed(a['resource_type'],a['resource_id'],a['action'],owner)
            return {'allowed':yes,'reason':'可信权限规则允许。' if yes else '可信权限规则拒绝或没有匹配授权。'}
        if name=='device_list':
            return {'devices':[{k:cp(d[k]) for k in ('id','name','type','room_id','capabilities')} for d in self.state['devices'] if (not a.get('room_id') or d['room_id']==a['room_id']) and (not a.get('device_type') or d['type']==a['device_type']) and self.allowed('device',d['id'],name)]}
        if name=='device_get':
            d=self.find('devices',a['device_id']);self.permit('device',d['id'],name);return d
        if name=='device_set':
            d=self.device_changes(a['device_id'],a['changes'])
            if fault and fault['kind']=='delay':
                t={'id':self.new_id('TASK'),'owner_id':self.actor['id'],'operation':name,'target_id':d['id'],'status':'pending','progress_pct':0,'cancellable':True,'created_at':self.stamp(),'updated_at':self.stamp(),'result':None,'error':None}
                self.state['tasks'].append(t);self.jobs[t['id']]={'due':self.now+timedelta(milliseconds=fault['delay_ms']),'changes':cp(a['changes'])}
                return {'task':t}
            self.apply_device(d,a['changes']);return {'device':d}
        if name=='sensor_read':
            room=a['room_id'];self.permit('sensor',room,name)
            if room not in [x['id'] for x in self.state['home']['rooms']]:raise Failure('NOT_FOUND','房间不存在。')
            vals=[x for x in self.state['sensors'] if x['room_id']==room and x['metric'] in a['metrics']]
            if not vals:raise Failure('NOT_FOUND','没有所请求的传感器。')
            if any(not x['online'] for x in vals):raise Failure('DEVICE_OFFLINE','传感器离线。',True)
            return {'readings':vals}
        if name=='schedule_list':
            vals=[]
            for s in self.state['schedules']:
                if not self.allowed('schedule',s['id'],name,s['owner_id']):continue
                if a.get('status','active')!='all' and s['status']!=a.get('status','active'):continue
                if a.get('kind') and s['kind']!=a['kind']:continue
                at=self.next_time(s['when'],self.now)
                if a.get('from') and at<dt(a['from']) or a.get('to') and at>=dt(a['to']):continue
                vals.append((at,s['id'],s))
            return {'schedules':[x[2] for x in sorted(vals,key=lambda x:x[:2])]}
        if name=='schedule_create':
            self.permit('schedule','self',name,self.actor['id']);self.check_schedule(a['kind'],a['when'],a['payload'])
            s={'id':self.new_id('SCH'),'owner_id':self.actor['id'],**cp(a),'status':'active','created_at':self.stamp(),'updated_at':self.stamp(),'last_triggered_at':None}
            self.state['schedules'].append(s);return s
        if name in ('schedule_update','schedule_cancel'):
            s=self.owned('schedules',a['schedule_id'],'schedule',name)
            if name=='schedule_cancel' and s['status']=='cancelled':return s
            if name=='schedule_cancel' and s['status']=='completed':raise Failure('NOT_CANCELLABLE','安排已经完成，不能撤回已执行结果。')
            if s['status']!='active':raise Failure('CONFLICT','安排不是启用状态。')
            if name=='schedule_cancel':s['status']='cancelled'
            else:
                n={**cp(s),**cp(a['patch'])};self.check_schedule(n['kind'],n['when'],n['payload']);s.update(a['patch'])
            s['updated_at']=self.stamp();return s
        if name=='media_search':
            query=a['query'].strip().lower()
            return {'items':[m for m in sorted(self.state['media_catalog'],key=lambda x:x['id']) if self.allowed('media',m['id'],name) and (not a.get('media_type') or m['type']==a['media_type']) and (not query or query in m['title'].lower() or query in m['type'])]}
        if name=='media_play':
            m=self.find('media_catalog',a['content_id']);self.permit('media',m['id'],name)
            d=self.find('devices',a['device_id']);self.permit('device',d['id'],name)
            if not d['online']:raise Failure('DEVICE_OFFLINE','播放设备离线。',True)
            if d['type'] not in ('tv','speaker'):raise Failure('UNSUPPORTED_OPERATION','该设备不支持媒体播放。')
            existing=[p for p in self.state['playbacks'] if p['device_id']==d['id'] and p['status'] in ('playing','paused')]
            # Check all permissions before changing any old session.
            for previous in existing:self.permit('playback',previous['id'],'media_control',previous['owner_id'])
            for previous in existing:previous.update(status='stopped',updated_at=self.stamp())
            p={'id':self.new_id('PLAY'),'owner_id':self.actor['id'],'device_id':d['id'],'content_id':m['id'],'status':'playing','position_s':0,'updated_at':self.stamp()};self.state['playbacks'].append(p);return p
        if name=='media_control':
            p=self.owned('playbacks',a['playback_id'],'playback',name);d=self.find('devices',p['device_id']);self.permit('device',d['id'],name)
            if not d['online']:raise Failure('DEVICE_OFFLINE','播放设备离线。',True)
            if p['status'] in ('stopped','ended'):raise Failure('CONFLICT','播放会话已经结束。')
            if a['action']=='seek':
                if a['position_s']>self.find('media_catalog',p['content_id'])['duration_s']:raise Failure('OUT_OF_RANGE','进度超出媒体时长。')
                p['position_s']=a['position_s']
            else:p['status']={'pause':'paused','resume':'playing','stop':'stopped'}[a['action']]
            p['updated_at']=self.stamp();return p
        if name in ('task_get','task_cancel'):
            t=self.owned('tasks',a['task_id'],'task',name)
            if name=='task_cancel':
                if t['status'] not in ('pending','running') or not t['cancellable']:raise Failure('NOT_CANCELLABLE','任务已经提交或不能取消，不会回滚。')
                t.update(status='cancelled',cancellable=False,updated_at=self.stamp())
            return t
        raise Failure('UNSUPPORTED_OPERATION','未知工具。')
    def call(self,name,args,request_id=None):
        request_id=request_id or f'REQ_{len(self.trace)+1:04d}'
        identity=json.dumps([name,args],sort_keys=True,ensure_ascii=False)
        if request_id in self.cache:
            old,response=self.cache[request_id]
            if old==identity:return cp(response)
            return self.error(request_id,Failure('CONFLICT','请求ID已用于不同参数。'))
        before=cp(self.state);fault=None
        try:
            if name not in TOOLS:raise Failure('UNSUPPORTED_OPERATION','未知工具。')
            validate(args,TOOLS[name]['input_schema'])
            resource=next((args[x] for x in ('device_id','schedule_id','task_id','playback_id','room_id') if x in args),None)
            key=(name,resource);self.attempts[key]=self.attempts.get(key,0)+1
            for f in self.fixture['faults']:
                if f['tool_name']==name and f['resource_id'] in (None,resource) and self.attempts[key] in f['on_attempts']:fault=f;break
            if fault and fault['kind']!='delay':raise Failure({'offline':'DEVICE_OFFLINE','transient_failure':'TRANSIENT_FAILURE','timeout':'TIMEOUT'}[fault['kind']],'夹具注入的可重现故障。',True)
            data=cp(self._dispatch(name,args,fault));pending=name=='device_set' and 'task' in data
            response={'request_id':request_id,'ok':True,'status':'pending' if pending else 'succeeded','data':data,'error':None,'operation_id':data['task']['id'] if pending else None,'clock_time':self.stamp()}
        except Failure as e:response=self.error(request_id,e)
        except Exception as e:
            from jsonschema import ValidationError
            if isinstance(e,(ValidationError,ValueError,TypeError)):response=self.error(request_id,Failure('INVALID_ARGUMENT','参数格式不符合工具定义。'))
            else:raise
        if name in TOOLS:validate(response,TOOLS[name]['output_schema'])
        self.cache[request_id]=(identity,cp(response))
        self.trace.append({'call':{'tool_name':name,'arguments':cp(args)},'request_id':request_id,'response':cp(response),'state_before':before,'state_after':cp(self.state),'node_id':self.current_node_id,'user_turn_index':self.current_user_turn_index or None})
        self.snapshots.append(cp(self.state));self.advance(self.state['clock']['advance_after_tool_call_ms'])
        return response
    def error(self,r,e):return {'request_id':r,'ok':False,'status':'failed','data':None,'error':{'code':e.code,'message':e.message,'retryable':e.retryable},'operation_id':None,'clock_time':self.stamp()}
    def advance(self,milliseconds):
        target=self.now+timedelta(milliseconds=milliseconds)
        while True:
            events=[]
            for e in self.fixture['external_events']:
                if e['id'] not in self.fired and self.now<=dt(e['at'])<=target:events.append((dt(e['at']),0,e['id'],'external',e))
            for tid,j in self.jobs.items():
                t=self.find('tasks',tid)
                if t['status'] in ('pending','running') and self.now<=j['due']<=target:events.append((j['due'],1,tid,'job',j))
            for s in self.state['schedules']:
                if s['status']!='active':continue
                after=max(self.now-timedelta(microseconds=1),dt(s['last_triggered_at']) if s['last_triggered_at'] else self.now-timedelta(microseconds=1))
                at=self.next_time(s['when'],after)
                if self.now<=at<=target:events.append((at,2,s['id'],'schedule',s))
            if not events:break
            at,_,eid,kind,obj=min(events,key=lambda e:e[:3]);self.now=at
            if kind=='external':
                self.fired.add(eid)
                if obj['type']=='device_change':self.apply_device(self.find('devices',obj['target_id']),obj['changes'])
                else:self.find('sensors',obj['target_id']).update(value=obj['sensor_value'],observed_at=self.stamp())
            elif kind=='job':
                t=self.find('tasks',eid)
                try:
                    d=self.device_changes(t['target_id'],obj['changes']);self.apply_device(d,obj['changes']);t.update(status='committed',progress_pct=100,result={'device':cp(d)})
                except Failure as e:t.update(status='failed',error={'code':e.code,'message':e.message,'retryable':e.retryable})
                t.update(cancellable=False,updated_at=self.stamp())
            else:
                obj.update(last_triggered_at=self.stamp(),updated_at=self.stamp())
                if obj['when']['mode']=='once':obj['status']='completed'
                if obj['kind']=='device_action':
                    for a in obj['payload']['actions']:
                        tid=self.new_id('TASK');t={'id':tid,'owner_id':obj['owner_id'],'operation':'schedule_trigger','target_id':a['device_id'],'status':'committed','progress_pct':100,'cancellable':False,'created_at':self.stamp(),'updated_at':self.stamp(),'result':None,'error':None}
                        try:
                            d=self.device_changes(a['device_id'],a['changes']);self.apply_device(d,a['changes']);t['result']={'device':cp(d)}
                        except Failure as e:t.update(status='failed',error={'code':e.code,'message':e.message,'retryable':e.retryable})
                        self.state['tasks'].append(t)
            self.state['clock']['current_at']=self.stamp();self.snapshots.append(cp(self.state))
        self.now=target;self.state['clock']['current_at']=self.stamp()
    def end_turn(self,node_id):
        received_node=self.current_node_id or node_id;turn_index=self.current_user_turn_index or len(self.turn_ranges)+1
        for e in self.trace[self.turn_start:]:
            if e.get('node_id') is None:e.update(node_id=received_node,user_turn_index=turn_index)
        self.turn_ranges.append({'node_id':received_node,'checkpoint_node_id':node_id,'user_turn_index':turn_index,'start':self.turn_start,'end':len(self.trace)})
        self.turn_start=len(self.trace);self.current_node_id=None;self.current_user_turn_index=0
        self.checkpoints[node_id]=cp(self.state);self.advance(self.state['clock']['advance_after_user_turn_ms'])
